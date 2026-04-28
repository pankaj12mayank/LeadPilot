from __future__ import annotations

import config

from backend.app.middleware.jwt import create_access_token


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
    assert body["schedule_timing"]["saturday_linkedin"] == "0 10 * * 6"


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
