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


def _safe_int(value: Any, default: int, *, min_value: int, max_value: int) -> int:
    try:
        return max(min_value, min(max_value, int(value)))
    except (TypeError, ValueError):
        return default


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _clean_lower_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip().lower().replace("-", "_")
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _normalize_priority(value: Any, default: str) -> str:
    text = str(value or default).strip().lower()
    return text if text in {"high", "medium", "low"} else default


def _default_source_registry() -> list[dict[str, str | bool]]:
    return [
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
    ]


def _normalize_source_type(value: Any, default: str) -> str:
    text = str(value or default).strip().lower().replace("-", "_")
    return text if text in {"job_board", "directory", "local", "manual"} else default


def _normalize_input_type(value: Any, default: str) -> str:
    text = str(value or default).strip().lower()
    return text if text in {"url", "keyword", "file", "csv"} else default


def _clean_adapter_function(value: Any, default: str) -> str:
    text = str(value or default).strip()
    return text or default


def _normalize_source_registry(value: Any) -> list[dict[str, Any]]:
    defaults = {str(item["source_name"]): dict(item) for item in _default_source_registry()}
    raw_items = value if isinstance(value, list) else []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        source_name = str(item.get("source_name") or "").strip().lower().replace("-", "_")
        if not source_name:
            continue
        base = defaults.get(
            source_name,
            {
                "source_name": source_name,
                "source_type": "directory",
                "enabled": True,
                "input_type": "url",
                "adapter_function": "collect_companies_from_source_pages",
            },
        )
        defaults[source_name] = {
            "source_name": source_name,
            "source_type": _normalize_source_type(item.get("source_type"), str(base.get("source_type") or "directory")),
            "enabled": bool(item.get("enabled", base.get("enabled", True))),
            "input_type": _normalize_input_type(item.get("input_type"), str(base.get("input_type") or "url")),
            "adapter_function": _clean_adapter_function(
                item.get("adapter_function"), str(base.get("adapter_function") or "collect_companies_from_source_pages")
            ),
        }
    return list(defaults.values())


def get_admin_controls() -> dict[str, Any]:
    cfg = get_admin_config()
    targeting = cfg.get("targeting") or {}
    scoring = cfg.get("scoring_weights") or {}
    scheduler = cfg.get("scheduler_config") or {}
    return {
        "scoring_weights": {
            "role_relevance": _safe_int(scoring.get("role_weight"), 40, min_value=1, max_value=100),
            "company_size": _safe_int(scoring.get("company_size_weight"), 20, min_value=1, max_value=100),
            "signals": _safe_int(scoring.get("signal_weight"), 35, min_value=1, max_value=100),
            "data_completeness": _safe_int(scoring.get("data_weight"), 25, min_value=1, max_value=100),
            "base_factor_mix": _safe_int(scoring.get("base_factor_mix"), 10, min_value=1, max_value=100),
        },
        "targeting_filters": {
            "allowed_sources": get_enabled_ingestion_sources(),
            "min_company_score": _safe_int(targeting.get("min_company_score"), 70, min_value=0, max_value=100),
            "preferred_locations": _clean_list(targeting.get("preferred_locations")),
            "preferred_keywords": _clean_list(targeting.get("preferred_keywords")),
        },
        "schedule_timing": {
            "daily_auto": str(scheduler.get("daily_auto") or "0 2 * * *"),
            "friday_heavy": str(scheduler.get("friday_heavy") or "0 3 * * 5"),
            "saturday_linkedin": str(scheduler.get("saturday_linkedin") or "0 10 * * 6"),
            "sunday_report": str(scheduler.get("sunday_report") or "0 18 * * 0"),
        },
    }


def get_admin_config() -> dict[str, Any]:
    s = settings_service.load_settings()
    raw = s.get("admin_config")
    if not isinstance(raw, dict):
        raw = {}

    t = raw.get("targeting")
    if not isinstance(t, dict):
        t = {}
    src = raw.get("sources")
    if not isinstance(src, dict):
        src = {}
    sw = raw.get("scoring_weights")
    if not isinstance(sw, dict):
        sw = {}
    sig = raw.get("signals_config")
    if not isinstance(sig, dict):
        sig = {}
    sch = raw.get("scheduler_config")
    if not isinstance(sch, dict):
        sch = {}
    sess = raw.get("session_policy")
    if not isinstance(sess, dict):
        sess = {}
    rp = raw.get("retry_policy")
    if not isinstance(rp, dict):
        rp = {}
    tp = raw.get("task_priority")
    if not isinstance(tp, dict):
        tp = {}
    wc = raw.get("worker_config")
    if not isinstance(wc, dict):
        wc = {}
    legacy = s.get("admin_controls")
    if not isinstance(legacy, dict):
        legacy = {}
    legacy_sw = legacy.get("scoring_weights")
    if not isinstance(legacy_sw, dict):
        legacy_sw = {}
    legacy_tf = legacy.get("targeting_filters")
    if not isinstance(legacy_tf, dict):
        legacy_tf = {}
    legacy_st = legacy.get("schedule_timing")
    if not isinstance(legacy_st, dict):
        legacy_st = {}

    return {
        "targeting": {
            "keywords": _clean_list(t.get("keywords")),
            "locations": _clean_list(t.get("locations")),
            "industries": _clean_list(t.get("industries")),
            "company_types": _clean_list(t.get("company_types")),
            "preferred_locations": _clean_list(t.get("preferred_locations") or legacy_tf.get("preferred_locations")),
            "preferred_keywords": _clean_list(t.get("preferred_keywords") or legacy_tf.get("preferred_keywords")),
            "min_company_score": _safe_int(
                t.get("min_company_score", legacy_tf.get("min_company_score", 70)),
                70,
                min_value=0,
                max_value=100,
            ),
        },
        "sources": {
            "job_boards": bool(src.get("job_boards", True)),
            "startup_directories": bool(src.get("startup_directories", True)),
            "local_listings": bool(src.get("local_listings", True)),
            "manual_seeds": bool(src.get("manual_seeds", True)),
            "allowed_sources": _clean_lower_list(
                src.get("allowed_sources")
                or legacy_tf.get("allowed_sources")
                or ["yc", "job_board", "local", "crunchbase", "builtwith", "manual"]
            ),
        },
        "scoring_weights": {
            "role_weight": _safe_int(sw.get("role_weight", legacy_sw.get("role_relevance", 40)), 40, min_value=1, max_value=100),
            "signal_weight": _safe_int(sw.get("signal_weight", legacy_sw.get("signals", 35)), 35, min_value=1, max_value=100),
            "data_weight": _safe_int(
                sw.get("data_weight", legacy_sw.get("data_completeness", 25)),
                25,
                min_value=1,
                max_value=100,
            ),
            "company_size_weight": _safe_int(
                sw.get("company_size_weight", legacy_sw.get("company_size", 20)),
                20,
                min_value=1,
                max_value=100,
            ),
            "base_factor_mix": _safe_int(
                sw.get("base_factor_mix", legacy_sw.get("base_factor_mix", 10)),
                10,
                min_value=1,
                max_value=100,
            ),
        },
        "signals_config": {
            "hiring_enabled": bool(sig.get("hiring_enabled", True)),
            "scaling_enabled": bool(sig.get("scaling_enabled", True)),
        },
        "scheduler_config": {
            "daily_time": str(sch.get("daily_time") or "02:00"),
            "weekly_time": str(sch.get("weekly_time") or "03:00"),
            "linkedin_day": str(sch.get("linkedin_day") or "sat").strip().lower()[:3] or "sat",
            "daily_auto": str(sch.get("daily_auto") or legacy_st.get("daily_auto") or "0 2 * * *"),
            "friday_heavy": str(sch.get("friday_heavy") or legacy_st.get("friday_heavy") or "0 3 * * 5"),
            "saturday_linkedin": str(sch.get("saturday_linkedin") or legacy_st.get("saturday_linkedin") or "0 10 * * 6"),
            "sunday_report": str(sch.get("sunday_report") or legacy_st.get("sunday_report") or "0 18 * * 0"),
        },
        "session_policy": {
            "expiry_days": _safe_int(sess.get("expiry_days"), 7, min_value=1, max_value=365),
        },
        "retry_policy": {
            "retry_count": _safe_int(rp.get("retry_count"), 3, min_value=1, max_value=10),
        },
        "task_priority": {
            "linkedin": _normalize_priority(tp.get("linkedin"), "high"),
            "scoring": _normalize_priority(tp.get("scoring"), "high"),
            "enrichment": _normalize_priority(tp.get("enrichment"), "medium"),
            "ingestion": _normalize_priority(tp.get("ingestion"), "low"),
        },
        "source_registry": _normalize_source_registry(raw.get("source_registry")),
        "worker_config": {
            "worker_count": _safe_int(wc.get("worker_count"), 3, min_value=1, max_value=64),
        },
    }


def get_source_registry() -> list[dict[str, Any]]:
    cfg = get_admin_config()
    return [dict(item) for item in (cfg.get("source_registry") or []) if isinstance(item, dict)]


def get_source_registry_names() -> list[str]:
    return [str(item.get("source_name") or "").strip().lower() for item in get_source_registry() if str(item.get("source_name") or "").strip()]


def get_source_registry_entry(source_name: str) -> dict[str, Any] | None:
    target = str(source_name or "").strip().lower().replace("-", "_")
    if not target:
        return None
    for item in get_source_registry():
        name = str(item.get("source_name") or "").strip().lower()
        if name == target:
            return dict(item)
    return None


def get_real_ingestion_source_names() -> list[str]:
    out: list[str] = []
    for item in get_source_registry():
        name = str(item.get("source_name") or "").strip().lower()
        input_type = str(item.get("input_type") or "").strip().lower()
        if not name or name == "manual":
            continue
        if input_type in {"csv", "file"}:
            continue
        out.append(name)
    return out


def get_enabled_ingestion_sources() -> list[str]:
    cfg = get_admin_config()
    src = cfg.get("sources") or {}
    requested = _clean_lower_list((src.get("allowed_sources") or []))
    out: list[str] = []
    for item in get_source_registry():
        name = str(item.get("source_name") or "").strip().lower()
        source_type = str(item.get("source_type") or "").strip().lower()
        if not name or not bool(item.get("enabled", True)):
            continue
        if source_type == "directory" and not bool(src.get("startup_directories", True)):
            continue
        if source_type == "job_board" and not bool(src.get("job_boards", True)):
            continue
        if source_type == "local" and not bool(src.get("local_listings", True)):
            continue
        if source_type == "manual" and not bool(src.get("manual_seeds", True)):
            continue
        out.append(name)
    # preserve order + de-dup
    seen: set[str] = set()
    uniq: list[str] = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    if requested:
        uniq = [name for name in uniq if name in set(requested)]
    return uniq


def get_min_company_score() -> int:
    cfg = get_admin_config()
    targeting = cfg.get("targeting") or {}
    return _safe_int(targeting.get("min_company_score"), 70, min_value=0, max_value=100)


def get_last_config_event() -> dict[str, Any] | None:
    event = settings_service.load_last_config_event()
    if not isinstance(event, dict):
        return None
    if str(event.get("event") or "").strip() != "config_updated":
        return None
    return {
        "event": "config_updated",
        "changed_fields": _clean_list(event.get("changed_fields")),
        "timestamp": str(event.get("timestamp") or "").strip(),
    }
