from __future__ import annotations

from typing import Any, Dict

from backend.safe_capture.ai_enricher import generate_message, generate_subject


def build_subject(lead: Dict[str, Any]) -> str:
    return generate_subject(lead)


def build_outreach_message(lead: Dict[str, Any]) -> str:
    return generate_message(lead)
