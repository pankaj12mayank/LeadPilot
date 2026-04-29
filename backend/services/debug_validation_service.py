from __future__ import annotations

from typing import Any

from sqlalchemy import text

from backend.services import runtime_settings
from database.orm.bootstrap import get_engine


def run_validation_checks() -> dict[str, Any]:
    cfg = runtime_settings.get_admin_config()
    pipeline_errors: list[str] = []
    db_errors: list[str] = []
    source_errors: list[str] = []

    try:
        enabled_sources = runtime_settings.get_enabled_ingestion_sources()
        if not enabled_sources:
            pipeline_errors.append("no_enabled_ingestion_sources")
    except Exception as e:  # noqa: BLE001
        pipeline_errors.append(f"enabled_sources_error:{e}")

    try:
        provider = runtime_settings.get_ai_provider()
        if provider not in {"ollama", "external_api", "none"}:
            pipeline_errors.append(f"invalid_ai_provider:{provider}")
    except Exception as e:  # noqa: BLE001
        pipeline_errors.append(f"ai_provider_error:{e}")

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT COUNT(1) FROM users"))
            conn.execute(text("SELECT COUNT(1) FROM leads"))
            conn.execute(text("SELECT COUNT(1) FROM companies"))
            conn.execute(text("SELECT COUNT(1) FROM company_enrichment"))
    except Exception as e:  # noqa: BLE001
        db_errors.append(str(e))

    try:
        registry = cfg.get("source_registry") or []
        for item in registry:
            if not isinstance(item, dict):
                source_errors.append("invalid_source_registry_entry")
                continue
            name = str(item.get("source_name") or "").strip()
            adapter = str(item.get("adapter_function") or "").strip()
            input_type = str(item.get("input_type") or "").strip().lower()
            if not name:
                source_errors.append("source_name_missing")
            if not adapter:
                source_errors.append(f"{name or 'unknown'}:adapter_missing")
            if input_type not in {"url", "keyword", "file", "csv"}:
                source_errors.append(f"{name or 'unknown'}:input_type_invalid")
    except Exception as e:  # noqa: BLE001
        source_errors.append(str(e))

    ok = not (pipeline_errors or db_errors or source_errors)
    return {
        "ok": ok,
        "pipeline_checks": {"ok": not pipeline_errors, "errors": pipeline_errors},
        "db_checks": {"ok": not db_errors, "errors": db_errors},
        "source_checks": {"ok": not source_errors, "errors": source_errors},
    }
