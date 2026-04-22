"""Backward-compatible entry; scoring lives in ``backend.lead_scoring``."""

from __future__ import annotations

from backend.lead_scoring.engine import normalize_lead_for_scoring, score_lead

__all__ = ["score_lead", "normalize_lead_for_scoring"]
