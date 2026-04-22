from __future__ import annotations

from typing import Any, Dict

from backend.ollama_messaging.generator import generate_lead_messages
from backend.ollama_messaging.types import LeadMessageInput
from backend.safe_capture.ai_enricher import generate_message as _gen_message
from backend.safe_capture.ai_enricher import generate_subject as _gen_subject


def generate_subject(lead: Dict[str, Any]) -> str:
    return _gen_subject(lead)


def generate_message(lead: Dict[str, Any]) -> str:
    return _gen_message(lead)


def lead_dict_to_message_input(lead: Dict[str, Any]) -> LeadMessageInput:
    """Map a generic lead dict to :class:`LeadMessageInput` for the Ollama pack generator."""
    return {
        "name": str(lead.get("name") or lead.get("full_name") or "").strip(),
        "company": str(lead.get("company") or lead.get("company_name") or "").strip(),
        "industry": str(lead.get("industry") or "").strip(),
        "job_title": str(lead.get("job_title") or lead.get("title") or "").strip(),
        "company_website": str(
            lead.get("company_website") or lead.get("website") or ""
        ).strip(),
        "pain_points": str(lead.get("pain_points") or lead.get("notes") or "").strip(),
        "opportunity_summary": str(lead.get("opportunity_summary") or "").strip(),
    }


def generate_message_pack(
    lead: Dict[str, Any],
    *,
    model_family: str = "llama3",
) -> Dict[str, str]:
    """Return linkedin_message, email_message, followup_message, short_summary, pain_points."""
    inp = lead_dict_to_message_input(lead)
    return dict(generate_lead_messages(inp, model_family=model_family))
