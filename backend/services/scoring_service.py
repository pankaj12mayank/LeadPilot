from __future__ import annotations

from typing import Any, Dict

from backend.lead_scoring.engine import score_lead


def score(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Full score payload (``score``, ``tier``, ``reason``, ``explanation``, ``breakdown``, ``reasons``)."""
    return score_lead(lead)
