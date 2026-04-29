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
        enabled = bool(config.USE_OLLAMA)
    else:
        enabled = _truthy(v, bool(config.USE_OLLAMA))
    ai = (get_admin_config().get("ai_control") or {})
    return enabled and bool(ai.get("ollama_enabled", True))


def get_free_api_mode() -> bool:
    s = settings_service.load_settings()
    v = s.get("free_api_mode")
    if v is None or v == "":
        return bool(config.FREE_API_MODE)
    return _truthy(v, bool(config.FREE_API_MODE))


def get_ai_provider() -> str:
    s = settings_service.load_settings()
    v = (s.get("ai_provider") or "ollama").strip().lower()
    provider = v if v in ("ollama", "external_api") else "ollama"
    ai = get_admin_config().get("ai_control") or {}
    ollama_enabled = bool(ai.get("ollama_enabled", True))
    api_enabled = bool(ai.get("api_enabled", True))
    if provider == "external_api" and not api_enabled:
        return "ollama" if ollama_enabled else "none"
    if provider == "ollama" and not ollama_enabled:
        return "external_api" if api_enabled else "none"
    return provider


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


def get_debug_mode() -> bool:
    s = settings_service.load_settings()
    v = s.get("debug_mode")
    if v is None or v == "":
        return bool(getattr(config, "DEBUG", False))
    return _truthy(v, bool(getattr(config, "DEBUG", False)))


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
            "source_name": "linkedin",
            "source_type": "directory",
            "enabled": True,
            "input_type": "keyword",
            "adapter_function": "collect_companies_from_source_pages",
        },
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
            "source_name": "google_maps",
            "source_type": "directory",
            "enabled": True,
            "input_type": "keyword",
            "adapter_function": "collect_companies_from_source_pages",
        },
        {
            "source_name": "indiamart",
            "source_type": "directory",
            "enabled": True,
            "input_type": "keyword",
            "adapter_function": "collect_companies_from_source_pages",
        },
        {
            "source_name": "justdial",
            "source_type": "directory",
            "enabled": True,
            "input_type": "keyword",
            "adapter_function": "collect_companies_from_source_pages",
        },
        {
            "source_name": "eworldtrade",
            "source_type": "directory",
            "enabled": True,
            "input_type": "keyword",
            "adapter_function": "collect_companies_from_source_pages",
        },
        {
            "source_name": "global_sources",
            "source_type": "directory",
            "enabled": True,
            "input_type": "keyword",
            "adapter_function": "collect_companies_from_source_pages",
        },
        {
            "source_name": "thomasnet",
            "source_type": "directory",
            "enabled": True,
            "input_type": "keyword",
            "adapter_function": "collect_companies_from_source_pages",
        },
        {
            "source_name": "yelp",
            "source_type": "directory",
            "enabled": True,
            "input_type": "keyword",
            "adapter_function": "collect_companies_from_source_pages",
        },
        {
            "source_name": "faire",
            "source_type": "directory",
            "enabled": True,
            "input_type": "keyword",
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
    return text if text in {"job_board", "directory", "local", "manual", "marketplace"} else default


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


def _default_plan_channel_access() -> dict[str, dict[str, Any]]:
    return {
        "starter": {
            "channels": ["linkedin", "public_db"],
            "lead_limit": 100,
        },
        "growth": {
            "channels": ["linkedin", "public_db", "google_maps", "indiamart", "justdial"],
            "lead_limit": 500,
        },
        "pro": {
            "channels": [
                "linkedin",
                "public_db",
                "google_maps",
                "indiamart",
                "justdial",
                "eworldtrade",
                "global_sources",
                "thomasnet",
                "yelp",
                "faire",
            ],
            "lead_limit": 2000,
        },
        "enterprise": {
            "channels": [
                "linkedin",
                "public_db",
                "google_maps",
                "indiamart",
                "justdial",
                "eworldtrade",
                "global_sources",
                "thomasnet",
                "yelp",
                "faire",
                "yc",
                "crunchbase",
                "job_board",
                "local",
                "builtwith",
            ],
            "lead_limit": 10000,
        },
    }


def _normalize_plan_channel_access(value: Any) -> dict[str, dict[str, Any]]:
    defaults = _default_plan_channel_access()
    raw = value if isinstance(value, dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for plan_id, base in defaults.items():
        row = raw.get(plan_id) if isinstance(raw.get(plan_id), dict) else {}
        out[plan_id] = {
            "channels": _clean_lower_list(row.get("channels") or base.get("channels") or []),
            "lead_limit": _safe_int(row.get("lead_limit"), int(base.get("lead_limit") or 100), min_value=1, max_value=100000),
        }
    return out


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
    ai = raw.get("ai_control")
    if not isinstance(ai, dict):
        ai = {}
    sc = raw.get("scoring_control")
    if not isinstance(sc, dict):
        sc = {}
    sf = raw.get("safety_control")
    if not isinstance(sf, dict):
        sf = {}
    qp = raw.get("queue_priority")
    if not isinstance(qp, dict):
        qp = {}
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
            "linkedin": bool(src.get("linkedin", True)),
            "public_db": bool(src.get("public_db", True)),
            "google_maps": bool(src.get("google_maps", True)),
            "indiamart": bool(src.get("indiamart", True)),
            "justdial": bool(src.get("justdial", True)),
            "eworldtrade": bool(src.get("eworldtrade", True)),
            "global_sources": bool(src.get("global_sources", True)),
            "thomasnet": bool(src.get("thomasnet", True)),
            "yelp": bool(src.get("yelp", True)),
            "faire": bool(src.get("faire", True)),
            "allowed_sources": _clean_lower_list(
                src.get("allowed_sources")
                or legacy_tf.get("allowed_sources")
                or [
                    "linkedin",
                    "yc",
                    "job_board",
                    "local",
                    "crunchbase",
                    "builtwith",
                    "google_maps",
                    "indiamart",
                    "justdial",
                    "eworldtrade",
                    "global_sources",
                    "thomasnet",
                    "yelp",
                    "faire",
                    "manual",
                ]
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
        "ai_control": {
            "ollama_enabled": bool(ai.get("ollama_enabled", True)),
            "api_enabled": bool(ai.get("api_enabled", True)),
        },
        "scoring_control": {
            "role": _safe_int(sc.get("role"), 40, min_value=1, max_value=100),
            "signals": _safe_int(sc.get("signals"), 35, min_value=1, max_value=100),
            "ai_score": _safe_int(sc.get("ai_score"), 25, min_value=1, max_value=100),
        },
        "safety_control": {
            "delay_seconds": max(0.2, min(float(sf.get("delay_seconds") or 1.0), 8.0)),
            "batch_size": _safe_int(sf.get("batch_size"), 10, min_value=1, max_value=100),
            "retry_count": _safe_int(sf.get("retry_count"), 3, min_value=1, max_value=10),
            "pagination_limit": _safe_int(sf.get("pagination_limit"), 5, min_value=1, max_value=100),
        },
        "queue_priority": {
            "linkedin": _normalize_priority(qp.get("linkedin"), _normalize_priority(tp.get("linkedin"), "high")),
            "ai": _normalize_priority(qp.get("ai"), "high"),
            "others": _normalize_priority(qp.get("others"), "medium"),
        },
        "source_registry": _normalize_source_registry(raw.get("source_registry")),
        "worker_config": {
            "worker_count": _safe_int(wc.get("worker_count"), 3, min_value=1, max_value=64),
        },
        "plan_channel_access": _normalize_plan_channel_access(raw.get("plan_channel_access")),
    }


def get_plan_channel_access(plan_id: str) -> dict[str, Any]:
    cfg = get_admin_config()
    mapping = cfg.get("plan_channel_access") or {}
    pid = str(plan_id or "starter").strip().lower()
    row = mapping.get(pid)
    if not isinstance(row, dict):
        row = mapping.get("starter")
    if not isinstance(row, dict):
        row = _default_plan_channel_access()["starter"]
    return {
        "channels": _clean_lower_list(row.get("channels")),
        "lead_limit": _safe_int(row.get("lead_limit"), 100, min_value=1, max_value=100000),
    }


def apply_plan_access_to_admin_config(cfg: dict[str, Any], *, role: str, plan_id: str) -> dict[str, Any]:
    if str(role or "user").strip().lower() == "admin":
        return dict(cfg)
    access = get_plan_channel_access(plan_id)
    plan_channels = set(_clean_lower_list(access.get("channels")))
    out = dict(cfg)
    src = dict(out.get("sources") or {})
    requested = _clean_lower_list(src.get("allowed_sources") or [])
    if requested:
        src["allowed_sources"] = [x for x in requested if x in plan_channels]
    else:
        src["allowed_sources"] = sorted(plan_channels)
    # map source toggles to plan channels
    for source_key in ("linkedin", "public_db", "google_maps", "indiamart", "justdial", "eworldtrade", "global_sources", "thomasnet", "yelp", "faire"):
        src[source_key] = bool(src.get(source_key, True)) and source_key in plan_channels
    out["sources"] = src
    reg = []
    for item in (out.get("source_registry") or []):
        if not isinstance(item, dict):
            continue
        row = dict(item)
        name = str(row.get("source_name") or "").strip().lower()
        row["enabled"] = bool(row.get("enabled", True)) and (name in plan_channels or name in {"manual"})
        reg.append(row)
    out["source_registry"] = reg
    return out


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
        if name in {
            "linkedin",
            "google_maps",
            "indiamart",
            "justdial",
            "eworldtrade",
            "global_sources",
            "thomasnet",
            "yelp",
            "faire",
        } and not bool(src.get(name, True)):
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
