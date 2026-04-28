"""
Lead scoring engine: 1–100 score, Hot/Warm/Cold tiers, breakdown + structured logs.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from backend.lead_scoring.breakdown import ScoreBreakdown
from backend.lead_scoring.factors import (
    score_budget_potential,
    score_company_size,
    score_country,
    score_email_availability,
    score_industry_match,
    score_job_role,
    score_platform_source,
    score_website_availability,
)
from backend.lead_scoring.tiers import assign_tier
from backend.utils.logger import get_logger
from backend.services import runtime_settings

logger = get_logger(__name__)


def normalize_lead_for_scoring(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Unify legacy CRM keys with current SaaS lead shape."""
    return {
        "full_name": str(lead.get("full_name") or lead.get("name") or "").strip(),
        "title": str(lead.get("title") or lead.get("job_title") or "").strip(),
        "company_name": str(lead.get("company_name") or lead.get("company") or "").strip(),
        "company_size": str(lead.get("company_size") or lead.get("employees") or "").strip(),
        "industry": str(lead.get("industry") or "").strip(),
        "location": str(lead.get("location") or "").strip(),
        "country": str(lead.get("country") or "").strip(),
        "company_website": str(lead.get("company_website") or lead.get("website") or "").strip(),
        "email": str(lead.get("email") or "").strip(),
        "linkedin_url": str(lead.get("linkedin_url") or lead.get("profile_url") or "").strip(),
        "source_platform": str(lead.get("source_platform") or lead.get("platform") or "").strip(),
        "notes": str(lead.get("notes") or "").strip(),
        "lead_id": str(lead.get("lead_id") or lead.get("id") or "").strip(),
    }


def score_lead(
    lead: Dict[str, Any],
    *,
    benchmark_industry: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute score (1–100), tier (hot/warm/cold), explanation, and per-factor breakdown.

    Optional ``benchmark_industry`` (or env ``SCORING_BENCHMARK_INDUSTRY``) boosts
    ``industry_match`` when the lead text aligns.
    """
    L = normalize_lead_for_scoring(lead)
    bench = (benchmark_industry or os.getenv("SCORING_BENCHMARK_INDUSTRY", "") or "").strip()

    bd = ScoreBreakdown()
    pairs: List[tuple[str, tuple[float, str]]] = [
        ("company_size", score_company_size(L)),
        ("job_role", score_job_role(L)),
        ("country", score_country(L)),
        ("website_availability", score_website_availability(L)),
        ("email_availability", score_email_availability(L)),
        ("platform_source", score_platform_source(L)),
        ("industry_match", score_industry_match(L, bench or None)),
        ("budget_potential", score_budget_potential(L)),
    ]

    for attr, (pts, msg) in pairs:
        setattr(bd, attr, float(pts))
        bd.messages[attr] = msg

    raw = bd.raw_total
    controls = runtime_settings.get_admin_controls()
    w = controls.get("scoring_weights") or {}
    role_w = max(1.0, float(w.get("role_relevance") or 30))
    size_w = max(1.0, float(w.get("company_size") or 20))
    sig_w = max(1.0, float(w.get("signals") or 25))
    data_w = max(1.0, float(w.get("data_completeness") or 15))
    base_w = max(1.0, float(w.get("base_factor_mix") or 10))
    total_w = role_w + size_w + sig_w + data_w + base_w

    role_component = 0.0
    if "job_role" in bd.messages:
        role_component = min(role_w, max(0.0, (float(getattr(bd, "job_role", 0.0)) / 15.0) * role_w))
    size_component = 0.0
    if "company_size" in bd.messages:
        size_component = min(size_w, max(0.0, (float(getattr(bd, "company_size", 0.0)) / 12.0) * size_w))
    data_component = 0.0
    if str(L.get("company_website") or "").strip():
        data_component += data_w * 0.5
    if str(L.get("email") or "").strip():
        data_component += data_w * 0.5
    data_component = min(data_w, data_component)
    base_component = min(base_w, max(0.0, raw / 100.0 * base_w))
    # Step-5 extension: signal-based additive points (does not replace base scoring).
    signal_hiring = bool(lead.get("signal_hiring")) or bool(lead.get("has_careers"))
    signal_scaling = bool(lead.get("signal_scaling"))
    signal_content_gap = bool(lead.get("signal_content_gap")) or (
        "has_blog" in lead and not bool(lead.get("has_blog"))
    )
    signal_ads_gap = bool(lead.get("signal_ads_gap")) or (
        "ads_presence" in lead and not bool(lead.get("ads_presence"))
    )
    signal_points = 0.0
    if signal_hiring:
        signal_points += 8.0
    if signal_scaling:
        signal_points += 8.0
    if signal_content_gap:
        signal_points += 4.0
    if signal_ads_gap:
        signal_points += 4.0
    signal_component = min(sig_w, signal_points)
    if signal_component > 0:
        bd.messages["signal_extension"] = (
            f"Signals +{signal_component:.0f} (hiring={signal_hiring}, scaling={signal_scaling}, "
            f"content_gap={signal_content_gap}, ads_gap={signal_ads_gap})"
        )
    raw = (role_component + size_component + signal_component + data_component + base_component) * (100.0 / total_w)

    final = int(max(1, min(100, round(raw))))
    tier = assign_tier(final)
    explanation = " ".join(f"{k}: {v}" for k, v in bd.messages.items())
    reasons = list(bd.messages.values())

    lead_ref = L.get("lead_id") or L.get("full_name") or "unknown"
    logger.info(
        "lead_score | ref=%s score=%s tier=%s factors=%s",
        lead_ref,
        final,
        tier,
        bd.to_dict(),
    )

    out = {
        "score": float(final),
        "tier": tier,
        "reason": " | ".join(reasons[:12]) if reasons else "baseline",
        "explanation": explanation,
        "breakdown": bd.to_dict(),
        "reasons": reasons,
    }
    return out
