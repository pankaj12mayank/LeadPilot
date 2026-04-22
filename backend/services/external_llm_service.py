"""OpenAI-compatible chat completions for AI message generation."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import httpx

from backend.services import runtime_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def chat_completion_json(
    *,
    system: str,
    user: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: float = 120.0,
) -> Optional[str]:
    url = (base_url or runtime_settings.get_external_api_base_url()).strip()
    key = (api_key or runtime_settings.get_external_api_key()).strip()
    m = (model or runtime_settings.get_external_api_model()).strip()
    if not key:
        logger.warning("external API key missing")
        return None
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body: Dict[str, Any] = {
        "model": m,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
            r = client.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("External LLM request failed: %s", e)
        return None
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if not choices or not isinstance(choices, list):
        return None
    msg = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(msg, dict):
        return None
    content = msg.get("content")
    return str(content).strip() if content else None


def test_external_connection(
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Minimal request to validate key and endpoint."""
    text = chat_completion_json(
        system="You reply with exactly the word OK in JSON as {\"ok\":true}.",
        user='Reply as JSON only: {"ok":true}',
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=60.0,
    )
    if not text:
        return {"ok": False, "detail": "No response from API"}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and obj.get("ok") is True:
            return {"ok": True, "detail": "API responded with JSON"}
    except json.JSONDecodeError:
        pass
    if re.search(r"\bOK\b", text, re.I):
        return {"ok": True, "detail": "API responded (non-strict JSON)"}
    return {"ok": False, "detail": "Unexpected response body"}
