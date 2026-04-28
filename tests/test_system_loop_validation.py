from __future__ import annotations

import uuid
from unittest.mock import patch

import config


def _api(subpath: str) -> str:
    p = subpath if subpath.startswith("/") else f"/{subpath}"
    root = (config.API_ROOT_PATH or "").rstrip("/")
    return f"{root}{p}" if root else p


def _token(client) -> str:
    email = f"pytest_{uuid.uuid4().hex[:12]}@example.com"
    password = "pytest-password-9"
    reg = client.post(_api("/auth/register"), json={"email": email, "password": password})
    assert reg.status_code == 200, reg.text
    return reg.json()["access_token"]


def test_full_system_loop_validation(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    # Seed one company to connect Saturday expansion with lead creation.
    seed = client.post(
        _api("/companies/ingest"),
        headers=hdr,
        json={"source": "manual", "companies": [{"company_name": "LoopCo", "website": "https://loopco.ai"}]},
    )
    assert seed.status_code == 200, seed.text
    listed = client.get(_api("/companies"), headers=hdr)
    assert listed.status_code == 200, listed.text
    company_row = next((x for x in listed.json() if x.get("domain") == "loopco.ai"), None)
    assert company_row is not None
    company_id = int(company_row["id"])

    # Cron -> data collection -> enrichment/signals/AI/scoring chain (safe mocked network).
    with patch(
        "backend.services.company_weekly_engine.company_ingestion_service.collect_companies_from_source_pages",
        return_value=([], {"pages_ok": 0, "pages_failed": 0, "candidates": 0}),
    ), patch(
        "backend.services.company_weekly_engine.company_enrichment_service.enrich_companies_batch",
        return_value={"selected": 1, "ok": 1, "failed": 0, "skipped": 0},
    ):
        daily = client.post(
            _api("/companies/scheduler/run"),
            headers=hdr,
            json={"job_type": "daily_auto"},
        )
    assert daily.status_code == 200, daily.text
    daily_body = daily.json()
    assert daily_body["job_type"] == "daily_auto"
    assert "result" in daily_body

    # Prepare company enrichment row so Saturday high-score candidate flow is connected.
    from backend.enrichment.website import WebsiteEnrichmentResult

    fake = WebsiteEnrichmentResult(
        url="https://loopco.ai",
        final_url="https://loopco.ai/",
        ok=True,
        has_blog=False,
        is_hiring=True,
        text_sample="LoopCo is hiring and scaling rapidly.",
    )
    with patch("backend.services.company_enrichment_service.fetch_website_enrichment", return_value=fake):
        enr = client.post(_api("/companies/enrich"), headers=hdr, json={"limit": 20})
    assert enr.status_code == 200, enr.text

    # LinkedIn expansion (manual) blocked when session expired.
    with patch(
        "backend.services.company_weekly_engine.session_info_dict",
        return_value={"has_cache": True, "within_policy": False, "policy_days": 7},
    ):
        sat_blocked = client.post(
            _api("/companies/scheduler/run"),
            headers=hdr,
            json={"job_type": "saturday_linkedin"},
        )
    assert sat_blocked.status_code == 200, sat_blocked.text
    assert sat_blocked.json()["result"]["paused"] is True

    # User login done -> manual profile conversion -> lead DB write.
    with patch(
        "backend.services.company_weekly_engine.session_info_dict",
        return_value={"has_cache": True, "within_policy": True, "policy_days": 7},
    ):
        sat_ok = client.post(
            _api("/companies/weekly-engine/run"),
            headers=hdr,
            json={
                "day": "sat",
                "saturday_min_score": 0,
                "saturday_limit": 25,
                "saturday_manual_profiles": [
                    {
                        "company_id": company_id,
                        "name": "Loop Founder",
                        "role": "Founder",
                        "profile_link": "https://www.linkedin.com/in/loop-founder",
                    }
                ],
            },
        )
    assert sat_ok.status_code == 200, sat_ok.text
    sat_body = sat_ok.json()
    assert sat_body["result"]["paused"] is False
    assert sat_body["result"]["conversion"]["created"] >= 1

    leads = client.get(_api("/leads"), headers=hdr)
    assert leads.status_code == 200, leads.text
    items = leads.json()["items"]
    created = next((x for x in items if x.get("linkedin_url") == "https://www.linkedin.com/in/loop-founder"), None)
    assert created is not None
    lead_id = str(created["id"])

    # User outreach -> status update.
    st = client.patch(
        _api(f"/leads/{lead_id}/status"),
        headers=hdr,
        json={"status": "contacted"},
    )
    assert st.status_code == 200, st.text
    assert st.json().get("status") in {"contacted", "message_sent", "request_sent"}

    # Next cycle cron run should still execute without broken linkages.
    with patch(
        "backend.services.company_weekly_engine.company_ingestion_service.collect_companies_from_source_pages",
        return_value=([], {"pages_ok": 0, "pages_failed": 0, "candidates": 0}),
    ), patch(
        "backend.services.company_weekly_engine.company_enrichment_service.enrich_companies_batch",
        return_value={"selected": 0, "ok": 0, "failed": 0, "skipped": 0},
    ):
        next_cycle = client.post(
            _api("/companies/scheduler/run"),
            headers=hdr,
            json={"job_type": "daily_auto"},
        )
    assert next_cycle.status_code == 200, next_cycle.text
    assert next_cycle.json()["job_type"] == "daily_auto"
