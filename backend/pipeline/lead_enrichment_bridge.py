"""
Glue: website fetch → signals → email patterns → long ``opportunity_summary`` for Ollama.
Used by :mod:`backend.pipeline.lead_pipeline` only.
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, List, Tuple

from backend.enrichment import (
    WebsiteEnrichmentResult,
    build_signals,
    email_candidates_from_name_and_url,
    fetch_website_enrichment,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def _env_flag(name: str, default: str = "1") -> bool:
    return (os.environ.get(name, default) or default).strip().lower() in ("1", "true", "yes", "on")


def _inter_request_delay() -> None:
    if not _env_flag("LEADPIPELINE_WEBSITE_ENRICHMENT", "1"):
        return
    lo = float(os.environ.get("LEADPIPELINE_ENRICH_DELAY_MIN", "0.25") or "0.25")
    hi = float(os.environ.get("LEADPIPELINE_ENRICH_DELAY_MAX", "0.9") or "0.9")
    if hi < lo:
        lo, hi = hi, lo
    time.sleep(random.uniform(lo, hi))


def build_opportunity_summary(
    lead: Dict[str, Any],
    ws: WebsiteEnrichmentResult,
    signals: Dict[str, bool],
    email_list: List[str],
) -> str:
    """Plain-text block fed to Ollama as ``opportunity_summary`` (plus per-field company context)."""
    name = str(lead.get("full_name") or lead.get("name") or "").strip()
    company = str(lead.get("company_name") or lead.get("company") or "").strip()
    title = str(lead.get("title") or lead.get("job_title") or "").strip()
    industry = str(lead.get("industry") or "").strip()
    loc = str(lead.get("location") or "").strip()
    site_url = str(lead.get("company_website") or lead.get("website") or "").strip()

    parts: list[str] = [
        "=== Person & company (from lead list) ===",
        f"Name: {name}\nTitle: {title}\nCompany: {company}\nIndustry: {industry}\nLocation: {loc}\nWebsite: {site_url}",
        "=== Website scan (heuristic) ===",
        f"fetch_ok: {bool(ws and ws.ok)}  http: {getattr(ws, 'http_status', 0) or 0}  err: {getattr(ws, 'error', '') or 'none'}",
        f"has_blog: {getattr(ws, 'has_blog', False)}  is_hiring: {getattr(ws, 'is_hiring', False)}  ads_signal: {getattr(ws, 'ads_presence', False)}",
    ]
    if ws and ws.text_sample:
        parts.append("=== Page text sample (trimmed) ===\n" + (ws.text_sample or "")[:4500])
    parts.append("=== Business signals (use for 2–3 problem hypotheses + summary) ===\n" + json.dumps(signals, indent=0))
    if email_list:
        parts.append("=== Suggested email patterns (do not present as verified) ===\n" + "\n".join(f"- {e}" for e in email_list))
    return "\n\n".join(parts)


def enrich_lead_for_pipeline(lead: Dict[str, Any]) -> tuple[WebsiteEnrichmentResult, Dict[str, bool], List[str], str, bool]:
    """
    Returns ``(website_result, signals, email_candidates, opportunity_summary, website_ok)``.

    If ``LEADPIPELINE_WEBSITE_ENRICHMENT=0`` or no URL, site fetch is skipped.
    """
    if not _env_flag("LEADPIPELINE_WEBSITE_ENRICHMENT", "1"):
        ws = WebsiteEnrichmentResult()
        em = str(lead.get("company_website") or lead.get("website") or "").strip()
        if em:
            ws.url = em
        sig = build_signals(ws, lead)
        cands = email_candidates_from_name_and_url(
            str(lead.get("full_name") or lead.get("name") or ""),
            str(lead.get("company_website") or lead.get("website") or ""),
        )
        return ws, sig, cands, build_opportunity_summary(lead, ws, sig, cands), False

    url = str(lead.get("company_website") or lead.get("website") or "").strip()
    ws: WebsiteEnrichmentResult
    if url:
        _inter_request_delay()
        try:
            ws = fetch_website_enrichment(url)
        except Exception as e:  # noqa: BLE001
            logger.warning("website enrich failed: %s", e)
            ws = WebsiteEnrichmentResult(url=url, error=str(e)[:200])
    else:
        ws = WebsiteEnrichmentResult()
    sig = build_signals(ws, lead)
    cands = email_candidates_from_name_and_url(
        str(lead.get("full_name") or lead.get("name") or ""),
        str(lead.get("company_website") or lead.get("website") or ""),
    )
    ok = bool(ws and ws.ok)
    summary = build_opportunity_summary(lead, ws, sig, cands)
    return ws, sig, cands, summary, ok
