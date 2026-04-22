from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.deps import get_current_user
from backend.app.schemas.ai_messages import LeadAIMessageRequest, LeadAIMessageResponse
from backend.ollama_messaging.generator import generate_lead_messages
from backend.ollama_messaging.types import LeadMessageInput
from backend.services import history_service, runtime_settings

router = APIRouter(prefix="/ai/messages", tags=["ai-messages"])


def _default_model_family() -> str:
    name = (runtime_settings.get_model_name() or "llama3").lower()
    if "mistral" in name or "mixtral" in name:
        return "mistral"
    if "deepseek" in name:
        return "deepseek"
    return "llama3"


@router.post("/generate", response_model=LeadAIMessageResponse)
def generate_ai_messages(
    body: LeadAIMessageRequest,
    user: dict = Depends(get_current_user),
) -> LeadAIMessageResponse:
    """Build LinkedIn, email, follow-up, summary, and pain points via Ollama with template fallback."""
    lead: LeadMessageInput = {
        "name": body.name,
        "company": body.company,
        "industry": body.industry,
        "job_title": body.job_title,
        "company_website": body.company_website,
        "pain_points": body.pain_points,
        "opportunity_summary": body.opportunity_summary,
    }
    family = body.model_family or _default_model_family()
    out = generate_lead_messages(lead, model_family=family)
    history_service.record_event(
        None,
        "ai.messages.generated",
        {"model_family": family, "has_company": bool(body.company.strip())},
        user["id"],
    )
    return LeadAIMessageResponse(**out)
