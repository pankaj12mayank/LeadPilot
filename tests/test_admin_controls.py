from __future__ import annotations

import config

from backend.app.middleware.jwt import create_access_token
from backend.services import runtime_settings, settings_service


def _api(subpath: str) -> str:
    p = subpath if subpath.startswith("/") else f"/{subpath}"
    root = (config.API_ROOT_PATH or "").rstrip("/")
    return f"{root}{p}" if root else p


def _admin_headers() -> dict[str, str]:
    tok = create_access_token("admin-test", {"admin": True})
    return {"Authorization": f"Bearer {tok}"}


def test_admin_controls_patch_and_get(client):
    hdr = _admin_headers()
    p = client.patch(
        _api("/admin/controls"),
        headers=hdr,
        json={
            "scoring_weights": {
                "role_relevance": 35,
                "company_size": 15,
                "signals": 30,
                "data_completeness": 10,
                "base_factor_mix": 10,
            },
            "targeting_filters": {
                "allowed_sources": ["yc", "job_board"],
                "min_company_score": 75,
                "preferred_locations": ["us", "india"],
                "preferred_keywords": ["saas"],
            },
            "schedule_timing": {
                "daily_auto": "0 2 * * *",
                "friday_heavy": "0 3 * * 5",
                "saturday_linkedin": "0 10 * * 6",
                "sunday_report": "0 18 * * 0",
            },
        },
    )
    assert p.status_code == 200, p.text
    got = client.get(_api("/admin/controls"), headers=hdr)
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["scoring_weights"]["signals"] == 30
    assert body["targeting_filters"]["min_company_score"] == 75
    assert body["targeting_filters"]["allowed_sources"] == ["yc", "job_board"]
    assert body["schedule_timing"]["saturday_linkedin"] == "0 10 * * 6"

    cfg = client.get(_api("/admin/config"), headers=hdr)
    assert cfg.status_code == 200, cfg.text
    cfg_body = cfg.json()
    assert cfg_body["targeting"]["min_company_score"] == 75
    assert cfg_body["targeting"]["preferred_keywords"] == ["saas"]
    assert cfg_body["sources"]["allowed_sources"] == ["yc", "job_board"]
    assert cfg_body["scheduler_config"]["saturday_linkedin"] == "0 10 * * 6"


def test_admin_stats_contains_total_companies(client):
    hdr = _admin_headers()
    r = client.get(_api("/admin/stats"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "total_companies" in body


def test_admin_job_logs_endpoint(client):
    hdr = _admin_headers()
    r = client.get(_api("/admin/job-logs"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "count" in body
    assert "items" in body


def test_admin_config_patch_and_get(client):
    hdr = _admin_headers()
    p = client.patch(
        _api("/admin/config"),
        headers=hdr,
        json={
            "targeting": {
                "keywords": ["saas", "agency"],
                "locations": ["india"],
                "industries": ["software"],
                "company_types": ["startup"],
            },
            "sources": {
                "job_boards": True,
                "startup_directories": True,
                "local_listings": False,
                "manual_seeds": True,
                "allowed_sources": ["yc", "job_board", "manual"],
            },
            "scoring_weights": {
                "role_weight": 45,
                "signal_weight": 35,
                "data_weight": 20,
                "company_size_weight": 18,
                "base_factor_mix": 12,
            },
            "signals_config": {"hiring_enabled": True, "scaling_enabled": True},
            "scheduler_config": {
                "daily_time": "02:00",
                "weekly_time": "03:00",
                "linkedin_day": "sat",
                "daily_auto": "0 2 * * *",
                "friday_heavy": "0 3 * * 5",
                "saturday_linkedin": "0 10 * * 6",
                "sunday_report": "0 18 * * 0",
            },
            "session_policy": {"expiry_days": 7},
            "retry_policy": {"retry_count": 4},
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
                    "source_name": "job_board",
                    "source_type": "job_board",
                    "enabled": False,
                    "input_type": "keyword",
                    "adapter_function": "collect_companies_from_source_pages",
                },
            ],
            "worker_config": {"worker_count": 4},
        },
    )
    assert p.status_code == 200, p.text
    got = client.get(_api("/admin/config"), headers=hdr)
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["targeting"]["keywords"] == ["saas", "agency"]
    assert body["sources"]["local_listings"] is False
    assert body["sources"]["allowed_sources"] == ["yc", "job_board", "manual"]
    assert body["scoring_weights"]["role_weight"] == 45
    assert body["scoring_weights"]["company_size_weight"] == 18
    assert body["session_policy"]["expiry_days"] == 7
    assert body["retry_policy"]["retry_count"] == 4
    assert body["task_priority"]["scoring"] == "high"
    registry = {item["source_name"]: item for item in body["source_registry"]}
    assert registry["yc"]["source_type"] == "directory"
    assert registry["job_board"]["enabled"] is False
    assert body["worker_config"]["worker_count"] == 4


def test_admin_config_patch_emits_config_updated_event(client):
    hdr = _admin_headers()
    seen: list[dict] = []

    def _listener(event: dict) -> None:
        seen.append(event)

    settings_service.subscribe_config_updates(_listener)
    try:
        p = client.patch(
            _api("/admin/config"),
            headers=hdr,
            json={
                "targeting": {
                    "keywords": ["fintech"],
                    "locations": ["uae"],
                    "industries": ["finance"],
                    "company_types": ["startup"],
                    "preferred_locations": ["dubai"],
                    "preferred_keywords": ["b2b"],
                    "min_company_score": 81,
                }
            },
        )
        assert p.status_code == 200, p.text
    finally:
        settings_service.unsubscribe_config_updates(_listener)

    assert seen, "expected config_updated listener notification"
    event = seen[-1]
    assert event["event"] == "config_updated"
    assert event["timestamp"]
    assert "admin_config.targeting.min_company_score" in event["changed_fields"]
    assert "admin_config.targeting.preferred_locations" in event["changed_fields"]

    last = runtime_settings.get_last_config_event()
    assert last is not None
    assert last["event"] == "config_updated"
    assert "admin_config.targeting.min_company_score" in last["changed_fields"]
    assert last["timestamp"]


def test_source_registry_drives_enabled_ingestion_sources(client):
    hdr = _admin_headers()
    p = client.patch(
        _api("/admin/config"),
        headers=hdr,
        json={
            "sources": {
                "job_boards": True,
                "startup_directories": True,
                "local_listings": True,
                "manual_seeds": True,
                "allowed_sources": ["yc", "job_board", "manual"],
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
                    "source_name": "job_board",
                    "source_type": "job_board",
                    "enabled": False,
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
            ],
        },
    )
    assert p.status_code == 200, p.text

    cfg = runtime_settings.get_admin_config()
    registry = {item["source_name"]: item for item in cfg["source_registry"]}
    assert registry["job_board"]["enabled"] is False
    assert registry["manual"]["input_type"] == "file"
    assert runtime_settings.get_enabled_ingestion_sources() == ["yc", "manual"]
