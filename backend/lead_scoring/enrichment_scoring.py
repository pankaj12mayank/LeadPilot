"""
Scoring with fixed weights (sum 100): role relevance, company size, signals, problems, data completeness.
Maps to the same ``tier`` assignment as the rest of the app (``assign_tier``).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.lead_scoring.factors import score_company_size, score_job_role
from backend.lead_scoring.tiers import assign_tier

# Max points per bucket (total 100)
W_ROLE = 30.0
W_SIZE = 20.0
W_SIGNALS = 25.0
W_PROBLEMS = 15.0
W_DATA = 10.0


def _scale(old: float, old_max: float, new_max: float) -> float:
    if old_max <= 0:
        return 0.0
    return min(new_max, max(0.0, (old / old_max) * new_max))


def _signal_points(signals: Dict[str, bool]) -> float:
    s = 0.0
    if signals.get("scaling"):
        s += 8.0
    if signals.get("hiring"):
        s += 7.0
    if signals.get("content_gap"):
        s += 5.0
    if signals.get("ads_gap"):
        s += 5.0
    return min(W_SIGNALS, s)


def _problem_points(pain: str) -> float:
    p = (pain or "").strip()
    if len(p) < 12:
        return 2.0
    lines = [x.strip() for x in re.split(r"[\n\r;]+|(?<=[.!?])\s+", p) if x.strip()]
    if not lines and p:
        lines = [p]
    # Reward structured bullets
    n_bullets = len([1 for L in p.splitlines() if re.match(r"^\s*[-*•]\s", L.strip())])
    base = 4.0 + 2.0 * min(4, len(lines)) + min(3.0, 1.0 * n_bullets)
    if len(p) > 200:
        base = min(W_PROBLEMS, base + 2.0)
    return min(W_PROBLEMS, max(1.0, base))


def _completeness_points(lead: Dict[str, Any], website_fetch_ok: bool) -> float:
    n = 0.0
    if str(lead.get("full_name") or lead.get("name") or "").strip():
        n += 2.0
    if str(lead.get("company_name") or lead.get("company") or "").strip():
        n += 2.0
    if str(lead.get("linkedin_url") or lead.get("profile_url") or "").strip():
        n += 2.0
    if str(lead.get("company_website") or lead.get("website") or "").strip():
        n += 2.0
    if website_fetch_ok:
        n += 1.0
    if str(lead.get("email") or "").strip():
        n += 1.0
    return min(W_DATA, n)


def score_lead_enriched(
    lead: Dict[str, Any],
    *,
    signals: Dict[str, bool],
    pain_points: str = "",
    website_fetch_ok: bool = False,
) -> Dict[str, Any]:
    """
    Return the same key shape as :func:`backend.lead_scoring.engine.score_lead`.
    """
    # Role & size reuse factor modules (old max 15 and 12 → rescale to 30 & 20)
    role_raw, rmsg = score_job_role(lead)
    size_raw, smsg = score_company_size(lead)
    role_pts = _scale(float(role_raw), 15.0, W_ROLE)
    size_pts = _scale(float(size_raw), 12.0, W_SIZE)

    sig_pts = _signal_points(signals)
    prob_pts = _problem_points(pain_points)
    comp_pts = _completeness_points(lead, website_fetch_ok)

    final = int(round(min(100.0, max(1.0, role_pts + size_pts + sig_pts + prob_pts + comp_pts))))
    tier = assign_tier(float(final))

    parts: List[str] = [rmsg, smsg]
    parts.append(
        f"Signals ({sig_pts:.0f}/{W_SIGNALS:.0f}): {signals.get('scaling')!s} scaling, "
        f"{signals.get('hiring')!s} hiring, {signals.get('content_gap')!s} content_gap, "
        f"{signals.get('ads_gap')!s} ads_gap"
    )
    parts.append(f"AI problems line weight ({prob_pts:.0f}/{W_PROBLEMS:.0f})")
    parts.append(f"Data fill ({comp_pts:.0f}/{W_DATA:.0f})")
    if website_fetch_ok:
        parts.append("Site fetch: OK")
    else:
        parts.append("Site fetch: skipped or failed (signals partly from public text only)")

    return {
        "score": float(final),
        "tier": tier,
        "reason": " | ".join(parts)[:2000],
        "explanation": " ".join(parts)[:4000],
        "breakdown": {
            "role": round(role_pts, 2),
            "company_size": round(size_pts, 2),
            "signals": round(sig_pts, 2),
            "problems": round(prob_pts, 2),
            "completeness": round(comp_pts, 2),
            "raw_factors": {
                "job_role_points": float(role_raw),
                "company_size_points": float(size_raw),
            },
        },
        "reasons": parts,
    }
