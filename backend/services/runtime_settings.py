"""Runtime overrides from data/runtime_settings.json (merged over process env)."""

from __future__ import annotations

from typing import Any

import config
from backend.services import settings_service


def _truthy(val: Any, default: bool) -> bool:
    if val is None:
        return default
    return str(val).lower() in ("1", "true", "yes", "on")


def get_model_name() -> str:
    s = settings_service.load_settings()
    v = s.get("model_name")
    if v is None or str(v).strip() == "":
        return config.MODEL_NAME
    return str(v).strip()


def get_use_ollama() -> bool:
    s = settings_service.load_settings()
    v = s.get("use_ollama")
    if v is None or v == "":
        return bool(config.USE_OLLAMA)
    return _truthy(v, bool(config.USE_OLLAMA))


def get_free_api_mode() -> bool:
    s = settings_service.load_settings()
    v = s.get("free_api_mode")
    if v is None or v == "":
        return bool(config.FREE_API_MODE)
    return _truthy(v, bool(config.FREE_API_MODE))


def get_ai_provider() -> str:
    s = settings_service.load_settings()
    v = (s.get("ai_provider") or "ollama").strip().lower()
    return v if v in ("ollama", "external_api") else "ollama"


def get_external_api_base_url() -> str:
    s = settings_service.load_settings()
    u = (s.get("external_api_base_url") or "").strip()
    return u or "https://api.openai.com/v1/chat/completions"


def get_external_api_key() -> str:
    s = settings_service.load_settings()
    return str(s.get("external_api_key") or "").strip()


def get_external_api_model() -> str:
    s = settings_service.load_settings()
    m = (s.get("external_api_model") or "").strip()
    return m or "gpt-4o-mini"


def get_branding() -> dict:
    s = settings_service.load_settings()
    b = s.get("branding")
    if not isinstance(b, dict):
        return {"product_name": "LeadPilot", "logo_url": "", "favicon_url": "", "footer_copyright": ""}
    return {
        "product_name": str(b.get("product_name") or "LeadPilot").strip() or "LeadPilot",
        "logo_url": str(b.get("logo_url") or "").strip(),
        "favicon_url": str(b.get("favicon_url") or "").strip(),
        "footer_copyright": str(b.get("footer_copyright") or "").strip()[:280],
    }


def get_smtp() -> dict[str, Any]:
    s = settings_service.load_settings()
    port = s.get("smtp_port")
    try:
        port_i = int(port) if port is not None and str(port).strip() != "" else config.SMTP_PORT
    except (TypeError, ValueError):
        port_i = config.SMTP_PORT
    pwd = config.SMTP_PASSWORD
    if "smtp_password" in s and s.get("smtp_password") is not None:
        pwd = s.get("smtp_password") or ""
    return {
        "host": (s.get("smtp_host") or config.SMTP_HOST or "").strip(),
        "port": port_i,
        "email": (s.get("smtp_email") or config.SMTP_EMAIL or "").strip(),
        "password": pwd,
        "use_tls": _truthy(
            s.get("smtp_use_tls") if "smtp_use_tls" in s else None,
            getattr(config, "SMTP_USE_TLS", True),
        ),
        "sender_name": (s.get("sender_name") or getattr(config, "SENDER_NAME", "Lead Engine") or "").strip(),
        "sender_email": (s.get("sender_email") or getattr(config, "SENDER_EMAIL", "") or "").strip()
        or (s.get("smtp_email") or config.SMTP_EMAIL or "").strip(),
        "signature": (s.get("email_signature") or getattr(config, "EMAIL_SIGNATURE", "") or "").replace(
            "\\n", "\n"
        ),
    }


def get_admin_controls() -> dict[str, Any]:
    s = settings_service.load_settings()
    raw = s.get("admin_controls")
    if not isinstance(raw, dict):
        raw = {}
    sw = raw.get("scoring_weights")
    if not isinstance(sw, dict):
        sw = {}
    tf = raw.get("targeting_filters")
    if not isinstance(tf, dict):
        tf = {}
    # Hard safety bounds
    out = {
        "scoring_weights": {
            "role_relevance": int(sw.get("role_relevance") or 30),
            "company_size": int(sw.get("company_size") or 20),
            "signals": int(sw.get("signals") or 25),
            "data_completeness": int(sw.get("data_completeness") or 15),
            "base_factor_mix": int(sw.get("base_factor_mix") or 10),
        },
        "targeting_filters": {
            "allowed_sources": list(tf.get("allowed_sources") or ["yc", "job_board", "local", "crunchbase", "builtwith", "manual"]),
            "min_company_score": int(tf.get("min_company_score") or 70),
            "preferred_locations": list(tf.get("preferred_locations") or []),
            "preferred_keywords": list(tf.get("preferred_keywords") or []),
        },
    }
    return out
