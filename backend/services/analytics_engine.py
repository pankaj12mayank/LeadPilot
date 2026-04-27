"""
Chart-ready analytics and KPIs for Lead Intelligence.

Cohort definition: leads whose ``created_at`` falls in the selected UTC window
(except ``period=all``, which includes every lead).

Rates are percentages (0–100) with two decimal places. Reply / meeting metrics use
available meta tables when present; see ``metrics.data_quality`` for coverage hints.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select

from database.orm.bootstrap import get_session_factory
from database.orm.models import Lead
from backend.services import email_history_service, history_service, status_history_service


CONTACT_STATUSES = frozenset(
    {
        "request_sent",
        "message_sent",
        "replied_got",
        "on_discussion",
        "interested",
        "deal",
        "close",
        "not_interested",
        "contacted",
        "replied",
        "follow_up_sent",
        "meeting_scheduled",
        "deal_discussion",
        "closed",
        "converted",
        "meeting_booked",
        "closed_won",
        "won",
    }
)
CLOSED_STATUSES = frozenset({"close", "closed", "converted", "closed_won", "won"})
MEETING_STATUSES = frozenset(
    {"on_discussion", "meeting_scheduled", "meeting_booked", "meeting", "booked"}
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(d: datetime) -> str:
    return d.isoformat()


def _parse_day_start(s: str) -> str:
    s = (s or "").strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return f"{s}T00:00:00+00:00"
    if "T" not in s:
        return _iso(_now())
    if s.endswith("Z"):
        return s[:-1] + "+00:00"
    return s


def _parse_day_end(s: str) -> str:
    s = (s or "").strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return f"{s}T23:59:59+00:00"
    if s.endswith("Z"):
        return s[:-1] + "+00:00"
    return s


def resolve_period(
    period: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Return ``(start_iso, end_iso, meta)``.

    Custom range wins when both ``date_from`` and ``date_to`` are provided.
    """
    now = _now()
    end_default = _iso(now)

    if date_from and date_to:
        start = _parse_day_start(date_from)
        end = _parse_day_end(date_to)
        if start > end:
            start, end = end, start
        return start, end, {"preset": "custom", "from": start, "to": end}

    p = (period or "30d").lower().strip()
    if p == "today":
        start = _iso(now.replace(hour=0, minute=0, second=0, microsecond=0))
        return start, end_default, {"preset": "today", "from": start, "to": end_default}
    if p in ("7d", "week", "7"):
        start = _iso(now - timedelta(days=7))
        return start, end_default, {"preset": "7d", "from": start, "to": end_default}
    if p in ("30d", "month", "30"):
        start = _iso(now - timedelta(days=30))
        return start, end_default, {"preset": "30d", "from": start, "to": end_default}
    if p in ("90d", "quarter", "90"):
        start = _iso(now - timedelta(days=90))
        return start, end_default, {"preset": "90d", "from": start, "to": end_default}
    if p in ("all", "lifetime", "*"):
        Session = get_session_factory()
        db = Session()
        try:
            row = db.scalar(select(func.min(Lead.created_at)))
            if row and str(row).strip():
                start = str(row).strip()
            else:
                start = "1970-01-01T00:00:00+00:00"
        finally:
            db.close()
        return start, end_default, {"preset": "all", "from": start, "to": end_default}

    start = _iso(now - timedelta(days=30))
    return start, end_default, {"preset": "30d", "from": start, "to": end_default}


def _load_cohort(start: str, end: str) -> List[Lead]:
    Session = get_session_factory()
    db = Session()
    try:
        return list(
            db.scalars(
                select(Lead).where(Lead.created_at >= start, Lead.created_at <= end).order_by(Lead.created_at.asc())
            )
        )
    finally:
        db.close()


def _pct(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return round(float(num) / float(den) * 100.0, 2)


def _lead_status(l: Lead) -> str:
    return str(l.status or "new").strip().lower() or "new"


def _lead_tier(l: Lead) -> str:
    return str(l.tier or "").strip().lower() or "unknown"


def _lead_platform(l: Lead) -> str:
    return str(l.source_platform or "unknown").strip().lower() or "unknown"


def _chart_bar_from_counter(c: Counter, *, label: str = "Leads") -> Dict[str, Any]:
    pairs = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "chart_type": "bar",
        "dataset_label": label,
        "labels": [k for k, _ in pairs],
        "values": [v for _, v in pairs],
        "points": [{"label": k, "value": int(v)} for k, v in pairs],
    }


def _chart_pie_from_counter(c: Counter) -> Dict[str, Any]:
    pairs = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
    total = sum(v for _, v in pairs) or 1
    return {
        "chart_type": "pie",
        "segments": [
            {"label": k, "value": int(v), "percent": round(v / total * 100, 2)} for k, v in pairs
        ],
    }


def _chart_line_daily(leads: List[Lead]) -> Dict[str, Any]:
    by_day: Counter[str] = Counter()
    for l in leads:
        ca = (l.created_at or "")[:10]
        if ca:
            by_day[ca] += 1
    days = sorted(by_day.keys())
    return {
        "chart_type": "line",
        "x_key": "date",
        "y_key": "new_leads",
        "series": [{"date": d, "new_leads": int(by_day[d])} for d in days],
    }


def _chart_funnel_stages(leads: List[Lead], events_meta: Dict[str, Any]) -> Dict[str, Any]:
    n = len(leads)
    st = Counter(_lead_status(x) for x in leads)
    engaged = sum(1 for l in leads if _lead_status(l) != "new" or (l.personalized_message or "").strip())
    contacted = sum(1 for l in leads if _lead_status(l) in CONTACT_STATUSES)
    meeting = sum(1 for l in leads if _lead_status(l) in MEETING_STATUSES)
    closed = sum(1 for l in leads if _lead_status(l) in CLOSED_STATUSES)

    raw = [
        {"key": "created", "label": "In cohort", "value": n},
        {"key": "engaged", "label": "Engaged", "value": engaged},
        {"key": "contacted", "label": "Contacted / advanced", "value": contacted},
        {"key": "meeting", "label": "Meeting booked", "value": meeting},
        {"key": "closed", "label": "Closed / won", "value": closed},
    ]
    # Monotonic funnel for classic visualization
    mono: List[Dict[str, Any]] = []
    cap = n
    for row in raw:
        v = min(cap, int(row["value"]))
        mono.append({**row, "value": v, "conversion_from_top_pct": _pct(v, n)})
        cap = v
    return {
        "chart_type": "funnel",
        "stages": mono,
        "status_counts": dict(st),
        "events_in_window": events_meta,
    }


def _chart_heatmap_platform_tier(leads: List[Lead]) -> Dict[str, Any]:
    plat_labels = sorted({_lead_platform(l) for l in leads})
    tier_labels = sorted({_lead_tier(l) for l in leads})
    if not plat_labels:
        plat_labels = ["—"]
    if not tier_labels:
        tier_labels = ["—"]
    idx_p = {p: i for i, p in enumerate(plat_labels)}
    idx_t = {t: i for i, t in enumerate(tier_labels)}
    matrix = [[0 for _ in plat_labels] for _ in tier_labels]
    for l in leads:
        pi = idx_p.get(_lead_platform(l), 0)
        ti = idx_t.get(_lead_tier(l), 0)
        matrix[ti][pi] += 1
    cells: List[Dict[str, Any]] = []
    for ti, tlab in enumerate(tier_labels):
        for pi, plab in enumerate(plat_labels):
            v = matrix[ti][pi]
            if v:
                cells.append({"x": plab, "y": tlab, "value": v})
    return {
        "chart_type": "heatmap",
        "x_labels": plat_labels,
        "y_labels": tier_labels,
        "matrix": matrix,
        "cells": cells,
    }


def _success_send_leads(start: str, end: str) -> frozenset:
    leads_out: set[str] = set()
    for e in history_service.list_events_between(start, end):
        if e.get("action") != "message.send_requested":
            continue
        lid = e.get("lead_id")
        if not lid:
            continue
        det = e.get("detail") or {}
        if isinstance(det, str):
            try:
                det = json.loads(det)
            except Exception:
                det = {}
        if isinstance(det, dict) and det.get("success") is True:
            leads_out.add(str(lid))
    return frozenset(leads_out)


def _compute_rates(
    leads: List[Lead],
    start: str,
    end: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    total = len(leads)
    statuses = [_lead_status(l) for l in leads]
    converted = sum(1 for s in statuses if s == "converted")
    contacted_status = sum(1 for s in statuses if s in CONTACT_STATUSES)
    meeting = sum(1 for s in statuses if s in MEETING_STATUSES)
    closed = sum(1 for s in statuses if s in CLOSED_STATUSES)

    sends = _success_send_leads(start, end)
    cohort_ids = {l.id for l in leads}
    touched_by_send = {lid for lid in sends if lid in cohort_ids}

    contacted_union = sum(
        1
        for l in leads
        if _lead_status(l) in CONTACT_STATUSES or l.id in touched_by_send
    )

    email_agg = email_history_service.aggregate_between(start, end)
    denom_reply = int(email_agg.get("distinct_leads_emailed") or 0)
    num_reply = int(email_agg.get("distinct_leads_replied") or 0)
    reply_rate = _pct(num_reply, denom_reply) if denom_reply else 0.0

    data_quality = {
        "reply_tracking": bool(denom_reply),
        "note": "Reply rate uses email_history rows with status containing 'reply' or 'replied'.",
    }

    metrics = {
        "total_leads": total,
        "conversion_rate_percent": _pct(converted, total),
        "contact_rate_percent": _pct(contacted_union, total),
        "reply_rate_percent": reply_rate,
        "meeting_booked_rate_percent": _pct(meeting, total),
        "closed_deal_rate_percent": _pct(closed, total),
        "leads_contacted_status": contacted_status,
        "leads_contacted_union_email": contacted_union,
        "leads_converted": converted,
        "leads_meeting_booked": meeting,
        "leads_closed_won": closed,
        "emails_sent_leads_distinct": denom_reply,
        "emails_replied_leads_distinct": num_reply,
    }
    return metrics, data_quality


def build_context(
    period: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
) -> Dict[str, Any]:
    start, end, meta = resolve_period(period, date_from, date_to)
    cohort = _load_cohort(start, end)
    events_meta = {
        "lead_history_actions": history_service.count_events_by_action_between(start, end),
        "status_transitions": len(status_history_service.list_changes_between(start, end)),
    }
    metrics, dq = _compute_rates(cohort, start, end)
    metrics["data_quality"] = dq

    by_platform = Counter(_lead_platform(l) for l in cohort)
    by_tier = Counter(_lead_tier(l) for l in cohort)
    by_status = Counter(_lead_status(l) for l in cohort)
    metrics["leads_by_platform"] = dict(by_platform)
    metrics["leads_by_tier"] = dict(by_tier)
    metrics["leads_by_status"] = dict(by_status)

    return {
        "period": meta,
        "window": {"start": start, "end": end},
        "cohort_size": len(cohort),
        "metrics": metrics,
        "counters": {
            "by_platform": dict(by_platform),
            "by_tier": dict(by_tier),
            "by_status": dict(by_status),
        },
        "cohort": cohort,
        "events_meta": events_meta,
    }


def overview(period: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    ctx = build_context(period, date_from, date_to)
    cohort: List[Lead] = ctx["cohort"]
    c_plat = Counter(ctx["counters"]["by_platform"])
    c_stat = Counter(ctx["counters"]["by_status"])
    return {
        "period": ctx["period"],
        "window": ctx["window"],
        "metrics": ctx["metrics"],
        "charts": {
            "bar": _chart_bar_from_counter(c_plat, label="Leads by platform"),
            "pie": _chart_pie_from_counter(c_stat),
            "line": _chart_line_daily(cohort),
            "funnel": _chart_funnel_stages(cohort, ctx["events_meta"]),
            "heatmap": _chart_heatmap_platform_tier(cohort),
        },
    }


def platforms_chart(period: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    ctx = build_context(period, date_from, date_to)
    c = Counter(ctx["counters"]["by_platform"])
    return {
        "period": ctx["period"],
        "window": ctx["window"],
        "metrics": {"total_leads": ctx["cohort_size"], "by_platform": dict(c)},
        "charts": {
            "bar": _chart_bar_from_counter(c, label="Leads by platform"),
            "pie": _chart_pie_from_counter(c),
        },
    }


def status_chart(period: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    ctx = build_context(period, date_from, date_to)
    c = Counter(ctx["counters"]["by_status"])
    return {
        "period": ctx["period"],
        "window": ctx["window"],
        "metrics": {"total_leads": ctx["cohort_size"], "by_status": dict(c)},
        "charts": {
            "bar": _chart_bar_from_counter(c, label="Leads by status"),
            "pie": _chart_pie_from_counter(c),
        },
    }


def conversion_view(period: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    ctx = build_context(period, date_from, date_to)
    m = ctx["metrics"]
    cohort = ctx["cohort"]
    series = [
        {"stage": "Conversion", "value": m["conversion_rate_percent"]},
        {"stage": "Contact", "value": m["contact_rate_percent"]},
        {"stage": "Reply", "value": m["reply_rate_percent"]},
        {"stage": "Meeting", "value": m["meeting_booked_rate_percent"]},
        {"stage": "Closed", "value": m["closed_deal_rate_percent"]},
    ]
    return {
        "period": ctx["period"],
        "window": ctx["window"],
        "metrics": {
            "total_leads": ctx["cohort_size"],
            "conversion_rate_percent": m["conversion_rate_percent"],
            "contact_rate_percent": m["contact_rate_percent"],
            "reply_rate_percent": m["reply_rate_percent"],
            "meeting_booked_rate_percent": m["meeting_booked_rate_percent"],
            "closed_deal_rate_percent": m["closed_deal_rate_percent"],
            "data_quality": m.get("data_quality"),
        },
        "charts": {
            "bar": {
                "chart_type": "bar",
                "dataset_label": "Rate %",
                "labels": [r["stage"] for r in series],
                "values": [r["value"] for r in series],
                "points": series,
            },
            "pie": _chart_pie_from_counter(
                Counter(
                    {
                        "converted": sum(1 for l in cohort if _lead_status(l) == "converted"),
                        "not_converted": max(0, len(cohort) - sum(1 for l in cohort if _lead_status(l) == "converted")),
                    }
                )
            ),
        },
    }


def timeline(period: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    ctx = build_context(period, date_from, date_to)
    cohort = ctx["cohort"]
    line = _chart_line_daily(cohort)
    # Second series: cumulative
    cum: List[Dict[str, Any]] = []
    running = 0
    for pt in line["series"]:
        running += int(pt.get("new_leads") or 0)
        cum.append({"date": pt["date"], "cumulative_leads": running})
    line["series_cumulative"] = cum
    return {
        "period": ctx["period"],
        "window": ctx["window"],
        "metrics": {"total_leads": ctx["cohort_size"]},
        "charts": {
            "line": line,
            "bar": _chart_bar_from_counter(
                Counter((l.created_at or "")[:10] for l in cohort if l.created_at),
                label="New leads / day",
            ),
        },
    }


def funnel(period: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    ctx = build_context(period, date_from, date_to)
    cohort = ctx["cohort"]
    funnel_chart = _chart_funnel_stages(cohort, ctx["events_meta"])
    transitions = status_history_service.list_changes_between(ctx["window"]["start"], ctx["window"]["end"])
    to_counts: Counter[str] = Counter()
    for t in transitions:
        ns = str(t.get("new_status") or "").lower()
        if ns:
            to_counts[ns] += 1
    return {
        "period": ctx["period"],
        "window": ctx["window"],
        "metrics": {
            "total_leads": ctx["cohort_size"],
            "status_transitions_in_window": len(transitions),
            "transitions_to_status": dict(to_counts),
        },
        "charts": {
            "funnel": funnel_chart,
            "bar": _chart_bar_from_counter(to_counts, label="Transitions into status"),
        },
    }


def tier_breakdown(period: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> Dict[str, Any]:
    """Optional extra helper — not a required route but useful internally."""
    ctx = build_context(period, date_from, date_to)
    c = Counter(ctx["counters"]["by_tier"])
    return {
        "period": ctx["period"],
        "window": ctx["window"],
        "metrics": {"by_tier": dict(c)},
        "charts": {
            "bar": _chart_bar_from_counter(c, label="Leads by tier"),
            "pie": _chart_pie_from_counter(c),
            "heatmap": _chart_heatmap_platform_tier(ctx["cohort"]),
        },
    }
