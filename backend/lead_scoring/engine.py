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
from backend.services.scoring_engine_service import composite_score
from backend.utils.logger import get_logger

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

    role_norm = min(1.0, max(0.0, float(getattr(bd, "job_role", 0.0)) / 15.0))
    size_norm = min(1.0, max(0.0, float(getattr(bd, "company_size", 0.0)) / 12.0))
    role_relevance = (((role_norm * 0.7) + (size_norm * 0.3)) * 100.0)

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
        signal_points += 40.0
    if signal_scaling:
        signal_points += 35.0
    if signal_content_gap:
        signal_points += 12.5
    if signal_ads_gap:
        signal_points += 12.5

    data_completeness = 0.0
    if str(L.get("company_website") or "").strip():
        data_completeness += 35.0
    if str(L.get("email") or "").strip():
        data_completeness += 35.0
    if str(L.get("linkedin_url") or "").strip():
        data_completeness += 15.0
    if str(lead.get("phone") or "").strip():
        data_completeness += 10.0
    if str(L.get("notes") or "").strip():
        data_completeness += 5.0

    ai_input = float(lead.get("ai_score") or 0.0)
    composite = composite_score(
        role_relevance=role_relevance,
        signals=min(100.0, signal_points),
        data_completeness=min(100.0, data_completeness),
        ai_score=ai_input,
    )
    final = int(round(float(composite["score"])))
    tier = assign_tier(final)
    bd.messages["weighted_components"] = (
        f"role={role_relevance:.1f}, signals={min(100.0, signal_points):.1f}, "
        f"data={min(100.0, data_completeness):.1f}, ai={ai_input:.1f}"
    )
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
    logger.debug("lead_score_breakdown ref=%s weighted=%s", lead_ref, composite)

    out = {
        "score": float(final),
        "tier": tier,
        "reason": " | ".join(reasons[:12]) if reasons else "baseline",
        "explanation": explanation,
        "breakdown": bd.to_dict(),
        "reasons": reasons,
    }
    return out
