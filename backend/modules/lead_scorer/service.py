from __future__ import annotations

from typing import Any, Dict

from backend.services.scoring_service import score


def score_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    return score(lead)
