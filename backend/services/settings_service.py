from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict

_ROOT = os.path.dirname(os.path.dirname(__file__))
SETTINGS_PATH = os.path.join(_ROOT, "data", "runtime_settings.json")
CONFIG_EVENT_PATH = os.path.join(_ROOT, "data", "config_last_event.json")
_EVENT_LOCK = Lock()
_CONFIG_LISTENERS: list = []


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
        "admin_controls": {
            "scoring_weights": {
                "role_relevance": 30,
                "company_size": 20,
                "signals": 25,
                "data_completeness": 15,
                "base_factor_mix": 10,
            },
            "targeting_filters": {
                "allowed_sources": ["yc", "job_board", "local", "crunchbase", "builtwith", "manual"],
                "min_company_score": 70,
                "preferred_locations": [],
                "preferred_keywords": [],
            },
            "schedule_timing": {
                "daily_auto": "0 2 * * *",
                "friday_heavy": "0 3 * * 5",
                "saturday_linkedin": "0 10 * * 6",
                "sunday_report": "0 18 * * 0",
            },
        },
        "admin_config": {
            "targeting": {
                "keywords": [],
                "locations": [],
                "industries": [],
                "company_types": [],
                "preferred_locations": [],
                "preferred_keywords": [],
                "min_company_score": 70,
            },
            "sources": {
                "job_boards": True,
                "startup_directories": True,
                "local_listings": True,
                "manual_seeds": True,
                "allowed_sources": ["yc", "job_board", "local", "crunchbase", "builtwith", "manual"],
            },
            "scoring_weights": {
                "role_weight": 40,
                "signal_weight": 35,
                "data_weight": 25,
                "company_size_weight": 20,
                "base_factor_mix": 10,
            },
            "signals_config": {
                "hiring_enabled": True,
                "scaling_enabled": True,
            },
            "scheduler_config": {
                "daily_time": "02:00",
                "weekly_time": "03:00",
                "linkedin_day": "sat",
                "daily_auto": "0 2 * * *",
                "friday_heavy": "0 3 * * 5",
                "saturday_linkedin": "0 10 * * 6",
                "sunday_report": "0 18 * * 0",
            },
            "session_policy": {
                "expiry_days": 7,
            },
            "retry_policy": {
                "retry_count": 3,
            },
            "task_priority": {
                "linkedin": "high",
                "scoring": "high",
                "enrichment": "medium",
                "ingestion": "low",
            },
            "source_registry": [
                {
                    "source_name": "yc",
                    "source_type": "directory",
                    "enabled": True,
                    "input_type": "url",
                    "adapter_function": "collect_companies_from_source_pages",
                },
                {
                    "source_name": "crunchbase",
                    "source_type": "directory",
                    "enabled": True,
                    "input_type": "url",
                    "adapter_function": "collect_companies_from_source_pages",
                },
                {
                    "source_name": "job_board",
                    "source_type": "job_board",
                    "enabled": True,
                    "input_type": "keyword",
                    "adapter_function": "collect_companies_from_source_pages",
                },
                {
                    "source_name": "local",
                    "source_type": "local",
                    "enabled": True,
                    "input_type": "keyword",
                    "adapter_function": "collect_companies_from_source_pages",
                },
                {
                    "source_name": "builtwith",
                    "source_type": "directory",
                    "enabled": True,
                    "input_type": "url",
                    "adapter_function": "collect_companies_from_source_pages",
                },
                {
                    "source_name": "manual",
                    "source_type": "manual",
                    "enabled": True,
                    "input_type": "file",
                    "adapter_function": "ingest_public_companies",
                },
            ],
            "worker_config": {
                "worker_count": 3,
            },
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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _compute_changed_fields(before: Any, after: Any, prefix: str = "") -> list[str]:
    if type(before) is not type(after):
        return [prefix] if prefix else []
    if isinstance(before, dict):
        changed: list[str] = []
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                changed.append(path)
                continue
            changed.extend(_compute_changed_fields(before.get(key), after.get(key), path))
        return changed
    if isinstance(before, list):
        return [prefix] if before != after and prefix else []
    return [prefix] if before != after and prefix else []


def _write_last_config_event(event: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CONFIG_EVENT_PATH), exist_ok=True)
    with open(CONFIG_EVENT_PATH, "w", encoding="utf-8") as f:
        json.dump(event, f, indent=2)
        f.write("\n")


def load_last_config_event() -> Dict[str, Any] | None:
    if not os.path.isfile(CONFIG_EVENT_PATH):
        return None
    try:
        with open(CONFIG_EVENT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def subscribe_config_updates(listener) -> Any:
    with _EVENT_LOCK:
        _CONFIG_LISTENERS.append(listener)
    return listener


def unsubscribe_config_updates(listener) -> None:
    with _EVENT_LOCK:
        try:
            _CONFIG_LISTENERS.remove(listener)
        except ValueError:
            pass


def _notify_config_listeners(event: Dict[str, Any]) -> None:
    with _EVENT_LOCK:
        listeners = list(_CONFIG_LISTENERS)
    for listener in listeners:
        try:
            listener(deepcopy(event))
        except Exception:
            continue


def emit_config_updated_event(changed_fields: list[str]) -> Dict[str, Any]:
    event = {
        "event": "config_updated",
        "changed_fields": sorted({str(x).strip() for x in changed_fields if str(x).strip()}),
        "timestamp": _utc_now_iso(),
    }
    _write_last_config_event(event)
    _notify_config_listeners(event)
    return event


def save_settings(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def patch_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    before = load_settings()
    cur = deepcopy(before)
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
    after = load_settings()
    changed_fields = _compute_changed_fields(before, after)
    if changed_fields:
        emit_config_updated_event(changed_fields)
    return after
