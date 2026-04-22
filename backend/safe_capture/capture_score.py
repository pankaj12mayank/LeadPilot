"""Deterministic lead scoring for the safe capture pipeline."""

from __future__ import annotations

import re
from typing import Any


_EXEC_TITLE_RE = re.compile(
    r"\b(founder|co[-\s]?founder|ceo|chief executive|owner|managing partner)\b",
    flags=re.IGNORECASE,
)

_INDUSTRY_BONUS_RE = re.compile(
    r"\b(saas|software as a service|marketing|real\s+estate|realtor|property)\b",
    flags=re.IGNORECASE,
)


def score_lead(lead: dict[str, Any], enrichment_meta: dict[str, Any] | None = None) -> tuple[int, str]:
    """
    Apply the Prompt 1 scoring rules and return ``(score, tier)``.

    Tiers: HOT >= 70, WARM 40-69, COLD < 40.
    """
    meta = enrichment_meta or {}
    score = 0

    title = str(lead.get("title") or "")
    name = str(lead.get("name") or "")
    haystack = f"{title} {name}".strip()
    if haystack and _EXEC_TITLE_RE.search(haystack):
        score += 30

    blob = " ".join(
        [
            str(lead.get("title") or ""),
            str(lead.get("company") or ""),
            str(lead.get("industry") or ""),
            str(lead.get("name") or ""),
        ]
    )
    if blob.strip() and _INDUSTRY_BONUS_RE.search(blob):
        score += 25

    if str(lead.get("company") or "").strip():
        score += 10

    if str(lead.get("website") or "").strip():
        score += 10

    if meta.get("startup_early_signal"):
        score += 10

    if score > 100:
        score = 100

    if score >= 70:
        tier = "HOT"
    elif score >= 40:
        tier = "WARM"
    else:
        tier = "COLD"

    return score, tier
