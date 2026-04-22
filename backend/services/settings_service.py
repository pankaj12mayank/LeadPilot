from __future__ import annotations

import json
import os
from typing import Any, Dict

_ROOT = os.path.dirname(os.path.dirname(__file__))
SETTINGS_PATH = os.path.join(_ROOT, "data", "runtime_settings.json")


def _defaults() -> Dict[str, Any]:
    return {
        "storage_mode": "csv",
        "notes": "Local runtime overrides; optional.",
        "smtp_host": "",
        "smtp_port": "",
        "smtp_email": "",
        "smtp_password": "",
        "smtp_use_tls": "",
        "sender_name": "",
        "sender_email": "",
        "email_signature": "",
        "platform_integrations": {},
        "ai_provider": "ollama",
        "external_api_base_url": "https://api.openai.com/v1/chat/completions",
        "external_api_key": "",
        "external_api_model": "gpt-4o-mini",
        "branding": {
            "product_name": "LeadPilot",
            "logo_url": "",
            "favicon_url": "",
            "footer_copyright": "",
        },
    }


def load_settings() -> Dict[str, Any]:
    if not os.path.isfile(SETTINGS_PATH):
        return _defaults()
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        base = _defaults()
        base.update(data)
        return base
    except Exception:
        return _defaults()


def save_settings(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def patch_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    cur = load_settings()
    for k, v in updates.items():
        if v is None:
            continue
        if k == "branding" and isinstance(v, dict):
            b = dict(cur.get("branding") or {})
            b.update(v)
            cur[k] = b
        else:
            cur[k] = v
    save_settings(cur)
    return load_settings()
