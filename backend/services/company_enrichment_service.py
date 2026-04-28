"""Website enrichment for companies (safe, timeout-limited, no heavy crawling)."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.enrichment.signals import build_signals
from backend.enrichment.website import fetch_website_enrichment
from backend.lead_scoring.tiers import assign_tier, tier_label
from backend.services import runtime_settings
from backend.settings.lead_schema import utc_now_iso
from database.orm.models import Company, CompanyEnrichment


def enrichment_to_dict(row: CompanyEnrichment | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "company_id": row.company_id,
        "source_url": row.source_url,
        "has_blog": bool(row.has_blog),
        "has_careers": bool(row.has_careers),
        "content_text": row.content_text or "",
        "signal_hiring": bool(row.signal_hiring),
        "signal_scaling": bool(row.signal_scaling),
        "signal_content_gap": bool(row.signal_content_gap),
        "signal_ads_gap": bool(row.signal_ads_gap),
        "score": float(row.score or 0),
        "priority": row.priority or "",
        "fetch_ok": bool(row.fetch_ok),
        "fetch_error": row.fetch_error or "",
        "last_checked": row.last_checked,
    }


def get_company_enrichment(db: Session, company_id: int) -> CompanyEnrichment | None:
    return db.scalar(select(CompanyEnrichment).where(CompanyEnrichment.company_id == int(company_id)).limit(1))


def _company_signal_score(*, signals: dict[str, bool], has_content: bool, website_present: bool, fetch_ok: bool) -> tuple[float, str]:
    controls = runtime_settings.get_admin_controls()
    w = controls.get("scoring_weights") or {}
    sig_w = max(1.0, float(w.get("signals") or 25))
    data_w = max(1.0, float(w.get("data_completeness") or 15))
    base_w = max(1.0, float(w.get("base_factor_mix") or 10))
    role_w = max(1.0, float(w.get("role_relevance") or 30))
    size_w = max(1.0, float(w.get("company_size") or 20))
    # Companies don't have role/size direct yet; fold them into base bucket proportionally.
    total_w = sig_w + data_w + base_w + role_w + size_w
    sig_pts = 0.0
    if signals.get("hiring"):
        sig_pts += sig_w * 0.4
    if signals.get("scaling"):
        sig_pts += sig_w * 0.35
    if signals.get("content_gap"):
        sig_pts += sig_w * 0.125
    if signals.get("ads_gap"):
        sig_pts += sig_w * 0.125
    sig_pts = min(sig_w, sig_pts)
    data_pts = 0.0
    if website_present:
        data_pts += data_w * 0.45
    if fetch_ok:
        data_pts += data_w * 0.35
    if has_content:
        data_pts += data_w * 0.20
    data_pts = min(data_w, data_pts)
    base_pts = base_w + role_w * 0.5 + size_w * 0.5
    score = max(0.0, min(100.0, (sig_pts + data_pts + base_pts) * (100.0 / total_w)))
    return score, tier_label(assign_tier(score))


def upsert_company_enrichment(
    db: Session,
    *,
    company: Company,
    timeout_seconds: float = 10.0,
    max_text_chars: int = 4000,
) -> CompanyEnrichment:
    """
    Enrich one company from homepage URL.

    Rules:
    - broken website -> keep enrichment row with ``fetch_ok=0`` and error text
    - timeout enforced via website fetch call
    - no deep scraping; homepage-only heuristics + short text sample
    """
    now = utc_now_iso()
    url = str(company.website or "").strip()
    existing = get_company_enrichment(db, company.id)
    if not url:
        if existing is None:
            existing = CompanyEnrichment(
                company_id=company.id,
                source_url="",
                has_blog=0,
                has_careers=0,
                content_text="",
                fetch_ok=0,
                fetch_error="missing_website",
                signal_hiring=0,
                signal_scaling=0,
                signal_content_gap=0,
                signal_ads_gap=0,
                score=0.0,
                priority="Cold",
                last_checked=now,
            )
            db.add(existing)
        else:
            existing.fetch_ok = 0
            existing.fetch_error = "missing_website"
            existing.signal_hiring = 0
            existing.signal_scaling = 0
            existing.signal_content_gap = 0
            existing.signal_ads_gap = 0
            existing.score = 0.0
            existing.priority = "Cold"
            existing.last_checked = now
        db.flush()
        db.refresh(existing)
        return existing

    ws = fetch_website_enrichment(url, timeout=float(timeout_seconds))
    if existing is None:
        existing = CompanyEnrichment(company_id=company.id)
        db.add(existing)
    existing.source_url = str(ws.final_url or ws.url or url)[:2000]
    existing.has_blog = 1 if ws.has_blog else 0
    existing.has_careers = 1 if ws.is_hiring else 0
    existing.content_text = str(ws.text_sample or "")[: max(200, int(max_text_chars))]
    sig = build_signals(
        ws,
        {
            "company_name": company.company_name,
            "website": company.website,
            "notes": ws.text_sample,
        },
    )
    existing.signal_hiring = 1 if sig.get("hiring") else 0
    existing.signal_scaling = 1 if sig.get("scaling") else 0
    existing.signal_content_gap = 1 if sig.get("content_gap") else 0
    existing.signal_ads_gap = 1 if sig.get("ads_gap") else 0
    sc, pri = _company_signal_score(
        signals=sig,
        has_content=bool(existing.content_text),
        website_present=bool(url),
        fetch_ok=bool(ws.ok),
    )
    existing.score = float(sc)
    existing.priority = str(pri)
    existing.fetch_ok = 1 if ws.ok else 0
    existing.fetch_error = str(ws.error or "")[:1500]
    existing.last_checked = now
    db.flush()
    db.refresh(existing)
    return existing


def enrich_companies_batch(
    db: Session,
    *,
    company_ids: list[int] | None = None,
    limit: int = 20,
    timeout_seconds: float = 10.0,
    delay_seconds: float = 0.4,
) -> dict[str, Any]:
    """
    Enrich up to ``limit`` companies (default 20) to keep requests light.
    """
    lim = max(1, min(int(limit or 20), 100))
    dly = max(0.1, min(float(delay_seconds or 0.4), 5.0))

    if company_ids:
        clean = [int(x) for x in company_ids if int(x) > 0][:lim]
        rows = list(db.scalars(select(Company).where(Company.id.in_(clean)).limit(lim)))
    else:
        rows = list(db.scalars(select(Company).order_by(Company.last_updated.desc(), Company.id.desc()).limit(lim)))
    ok = 0
    failed = 0
    skipped = 0
    for idx, c in enumerate(rows):
        if not str(c.website or "").strip():
            upsert_company_enrichment(db, company=c, timeout_seconds=timeout_seconds)
            skipped += 1
        else:
            enr = upsert_company_enrichment(db, company=c, timeout_seconds=timeout_seconds)
            if enr.fetch_ok:
                ok += 1
            else:
                failed += 1
        if idx < len(rows) - 1:
            time.sleep(dly)
    return {"selected": len(rows), "ok": ok, "failed": failed, "skipped": skipped}
