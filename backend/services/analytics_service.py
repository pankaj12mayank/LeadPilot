"""Dashboard and summary metrics using SQL aggregation (no full-table ORM scans)."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.orm.bootstrap import get_session_factory
from database.orm.models import Lead

_CACHE_TTL_SEC = 25.0
_dashboard_cache: Tuple[float, Dict[str, Any]] | None = None


def _invalidate_dashboard_cache() -> None:
    global _dashboard_cache
    _dashboard_cache = None


def _compute_metrics(db: Session) -> Dict[str, Any]:
    total = int(db.scalar(select(func.count(Lead.id))) or 0)

    by_status: Dict[str, int] = {}
    for st, cnt in db.execute(select(Lead.status, func.count(Lead.id)).group_by(Lead.status)):
        key = str(st if st is not None else "unknown")
        by_status[key] = int(cnt)

    by_platform: Dict[str, int] = {}
    for plat, cnt in db.execute(select(Lead.source_platform, func.count(Lead.id)).group_by(Lead.source_platform)):
        key = str(plat).strip() if plat is not None else ""
        key = key or "unknown"
        by_platform[key] = int(cnt)

    tier_rows = list(db.execute(select(func.lower(Lead.tier), func.count(Lead.id)).group_by(func.lower(Lead.tier))))
    tier_c = {str(t or ""): int(c) for t, c in tier_rows}
    hot = int(tier_c.get("hot", 0))
    warm = int(tier_c.get("warm", 0))
    cold = int(tier_c.get("cold", 0))

    contacted = int(
        db.scalar(select(func.count(Lead.id)).where(func.lower(Lead.status) == "contacted")) or 0
    )
    converted = int(
        db.scalar(
            select(func.count(Lead.id)).where(func.lower(Lead.status).in_(("converted", "closed")))
        )
        or 0
    )
    conv = (converted / total * 100.0) if total else 0.0

    ym_expr = func.substr(Lead.created_at, 1, 7)
    month_rows = db.execute(
        select(ym_expr.label("ym"), func.count(Lead.id))
        .where(Lead.created_at != "")
        .group_by(ym_expr)
        .order_by(ym_expr.asc())
    ).all()
    leads_by_month: List[Dict[str, Any]] = [{"month": str(m), "count": int(c)} for m, c in month_rows if m]

    stack: Dict[str, Dict[str, int]] = defaultdict(lambda: {"hot": 0, "warm": 0, "cold": 0})
    for plat, tier_l, cnt in db.execute(
        select(Lead.source_platform, func.lower(Lead.tier), func.count(Lead.id)).group_by(
            Lead.source_platform,
            func.lower(Lead.tier),
        )
    ):
        pkey = str(plat).strip() if plat is not None else ""
        pkey = pkey or "unknown"
        t = str(tier_l or "").lower()
        if t in ("hot", "warm", "cold"):
            stack[pkey][t] += int(cnt)

    tier_mix_by_platform = [
        {"platform": p, "hot": v["hot"], "warm": v["warm"], "cold": v["cold"]}
        for p, v in sorted(stack.items(), key=lambda x: x[0])
    ]

    return {
        "total": total,
        "by_status": dict(by_status),
        "by_platform": dict(by_platform),
        "total_leads": total,
        "hot_leads": hot,
        "warm_leads": warm,
        "cold_leads": cold,
        "tier_distribution": {"hot": hot, "warm": warm, "cold": cold},
        "contacted_leads": contacted,
        "converted_leads": converted,
        "conversion_rate_percent": round(conv, 2),
        "platform_distribution": dict(by_platform),
        "status_distribution": dict(by_status),
        "leads_by_month": leads_by_month,
        "tier_mix_by_platform": tier_mix_by_platform,
    }


def summary() -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        m = _compute_metrics(db)
        return {
            "total": m["total"],
            "by_status": m["by_status"],
            "by_platform": m["by_platform"],
        }
    finally:
        db.close()


def crm_metrics() -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        m = _compute_metrics(db)
        return {k: m[k] for k in m if k not in ("total", "by_status", "by_platform", "leads_by_month", "tier_mix_by_platform")}
    finally:
        db.close()


def dashboard(*, use_cache: bool = True) -> Dict[str, Any]:
    """API dashboard: aggregated lead metrics plus history volume. Cached briefly to reduce read load."""
    global _dashboard_cache
    now = time.monotonic()
    if use_cache and _dashboard_cache is not None:
        ts, payload = _dashboard_cache
        if (now - ts) < _CACHE_TTL_SEC:
            return dict(payload)

    Session = get_session_factory()
    db = Session()
    try:
        out = _compute_metrics(db)
        try:
            from backend.services import history_service

            out["recent_history_events"] = history_service.count_recent(7)
        except Exception:
            out["recent_history_events"] = 0
        _dashboard_cache = (now, dict(out))
        return dict(out)
    finally:
        db.close()


def invalidate_analytics_cache() -> None:
    """Call after bulk lead mutations so the next dashboard read is fresh."""
    _invalidate_dashboard_cache()
