from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

import config
from backend.ollama_messaging.fallback import build_fallback_pack, merge_with_fallback
from backend.ollama_messaging.ollama_service import OllamaGenerateService
from backend.ollama_messaging.types import LeadMessageInput, LeadMessageOutput, ModelFamily
from backend.services import external_llm_service, runtime_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_REQUIRED_KEYS = (
    "linkedin_message",
    "email_message",
    "followup_message",
    "short_summary",
    "pain_points",
)


def _read_prompt(name: str) -> str:
    path = _PROMPTS_DIR / name
    return path.read_text(encoding="utf-8").strip()


def _fill_user_template(lead: LeadMessageInput) -> str:
    tpl = _read_prompt("user_template.txt")
    return tpl.format(
        name=str(lead.get("name") or "").strip(),
        company=str(lead.get("company") or "").strip(),
        industry=str(lead.get("industry") or "").strip(),
        job_title=str(lead.get("job_title") or "").strip(),
        company_website=str(lead.get("company_website") or "").strip(),
        pain_points=str(lead.get("pain_points") or "").strip(),
        opportunity_summary=str(lead.get("opportunity_summary") or "").strip(),
    )


def _normalize_model_family(model_family: str) -> ModelFamily:
    m = (model_family or "llama3").lower().strip()
    if m in ("mistral", "mixtral"):
        return "mistral"
    if m in ("deepseek", "deep-seek", "deep_seek"):
        return "deepseek"
    return "llama3"


def _resolve_ollama_tag(model_family: ModelFamily) -> str:
    if model_family == "mistral":
        return str(getattr(config, "OLLAMA_MODEL_MISTRAL", "mistral") or "mistral").strip()
    if model_family == "deepseek":
        return str(getattr(config, "OLLAMA_MODEL_DEEPSEEK", "deepseek-r1") or "deepseek-r1").strip()
    return str(getattr(config, "OLLAMA_MODEL_LLAMA3", "llama3") or "llama3").strip()


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    return t.strip()


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    t = _strip_code_fences(raw)
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", t)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def generate_lead_messages(
    lead: LeadMessageInput,
    *,
    model_family: str = "llama3",
    ollama: Optional[OllamaGenerateService] = None,
) -> LeadMessageOutput:
    """
    Produce LinkedIn, email, follow-up, short company summary, and pain points.

    Uses Ollama when enabled; otherwise merges template fallbacks for any missing field.
    """
    family = _normalize_model_family(model_family)
    model_tag = _resolve_ollama_tag(family)

    if runtime_settings.get_free_api_mode():
        logger.info("free_api_mode; using template fallback")
        return build_fallback_pack(lead)

    system = _read_prompt("system.txt")
    user_prompt = _fill_user_template(lead)
    full_prompt = user_prompt

    provider = runtime_settings.get_ai_provider()
    raw: Optional[str] = None

    if provider == "external_api":
        if not runtime_settings.get_external_api_key():
            logger.warning("external_api selected but no API key; using template fallback")
            return build_fallback_pack(lead)
        raw = external_llm_service.chat_completion_json(system=system, user=full_prompt)
    elif provider == "ollama" and runtime_settings.get_use_ollama():
        client = ollama or OllamaGenerateService()
        raw = client.generate_text(model_tag, full_prompt, system=system)
    else:
        logger.info("Ollama disabled or provider not ollama; using template fallback")
        return build_fallback_pack(lead)

    if not raw:
        logger.warning("Using full template fallback (no Ollama text, model=%s)", model_tag)
        return build_fallback_pack(lead)

    data = _parse_json_object(raw)
    if not data:
        logger.warning("Using full template fallback (invalid JSON from model=%s)", model_tag)
        return build_fallback_pack(lead)

    merged = merge_with_fallback(data, lead)
    if all(str(data.get(k) or "").strip() for k in _REQUIRED_KEYS):
        logger.info("Ollama message pack OK (model=%s)", model_tag)
    else:
        logger.info("Ollama JSON partial; filled gaps from templates (model=%s)", model_tag)
    return merged
