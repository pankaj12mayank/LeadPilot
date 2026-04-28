from __future__ import annotations

import uuid

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


def test_companies_ingest_and_list(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    r = client.post(
        _api("/companies/ingest"),
        headers=hdr,
        json={
            "source": "mock",
            "companies": [
                {"company_name": "Acme", "website": "https://acme.com"},
                {"name": "Beta", "domain": "beta.io"},
                {"company_name": "Acme Refresh", "website": "http://www.acme.com/about", "source": "seed"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"created": 2, "updated": 1, "skipped": 0}

    listed = client.get(_api("/companies"), headers=hdr)
    assert listed.status_code == 200, listed.text
    items = listed.json()
    assert len(items) == 2
    assert any(x["domain"] == "acme.com" for x in items)

    one = client.get(_api("/companies/by-domain/acme.com"), headers=hdr)
    assert one.status_code == 200, one.text
    row = one.json()
    assert row["domain"] == "acme.com"
    assert row["company_name"] == "Acme Refresh"


def test_companies_ingest_real_sources(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    fake_candidates = [
        {"company_name": "Yc One", "website": "https://yc-one.com", "source": "yc"},
        {"company_name": "Yc Two", "website": "https://yc-two.dev", "source": "yc"},
    ]
    fake_stats = {"pages_ok": 1, "pages_failed": 0, "candidates": 2}
    with patch(
        "backend.app.routes.companies.company_ingestion_service.collect_companies_from_source_pages",
        return_value=(fake_candidates, fake_stats),
    ):
        r = client.post(
            _api("/companies/ingest-real"),
            headers=hdr,
            json={
                "source": "yc",
                "seed_urls": ["https://www.ycombinator.com/companies"],
                "batch_size": 10,
                "delay_seconds": 0.2,
                "max_companies": 50,
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "yc"
    assert body["fetched"]["candidates"] == 2
    assert body["saved"]["created"] >= 2


def test_companies_explorer_search_triggers_ingest_when_low_results(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    # ensure no direct DB hits for this keyword
    listed = client.get(_api("/companies"), headers=hdr)
    assert listed.status_code == 200, listed.text

    fake_candidates = [{"company_name": "Cloud Nova", "website": "https://cloudnova.ai", "source": "yc"}]
    fake_stats = {"pages_ok": 1, "pages_failed": 0, "candidates": 1}
    with patch(
        "backend.app.routes.companies.company_ingestion_service.collect_companies_from_source_pages",
        return_value=(fake_candidates, fake_stats),
    ):
        r = client.post(
            _api("/companies/explorer/search"),
            headers=hdr,
            json={
                "mode": "explorer",
                "keyword": "cloudnova",
                "location": "",
                "min_results": 1,
                "max_results": 20,
                "sources": ["yc"],
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "explorer"
    assert body["ingestion"]["triggered"] is True
    assert body["count"] >= 1
    assert any((x.get("domain") == "cloudnova.ai") for x in body["results"])


def test_companies_explorer_search_supports_filters_and_enriched_columns(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    seed = client.post(
        _api("/companies/ingest"),
        headers=hdr,
        json={"source": "yc", "companies": [{"company_name": "SignalFlow", "website": "https://signalflow.ai"}]},
    )
    assert seed.status_code == 200, seed.text

    from backend.enrichment.website import WebsiteEnrichmentResult

    fake = WebsiteEnrichmentResult(
        url="https://signalflow.ai",
        final_url="https://signalflow.ai/",
        ok=True,
        has_blog=False,
        is_hiring=True,
        text_sample="SignalFlow is hiring and expanding its GTM team fast.",
        ads_presence=False,
    )
    with patch("backend.services.company_enrichment_service.fetch_website_enrichment", return_value=fake):
        enr = client.post(_api("/companies/enrich"), headers=hdr, json={"limit": 20})
    assert enr.status_code == 200, enr.text

    r = client.post(
        _api("/companies/explorer/search"),
        headers=hdr,
        json={
            "mode": "explorer",
            "keyword": "",
            "source_filter": "yc",
            "min_score": 1,
            "signal_hiring": True,
            "signal_scaling": True,
            "min_results": 1,
            "max_results": 20,
            "sources": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] >= 1
    row = body["results"][0]
    assert row["company_name"] == "SignalFlow"
    assert row["source"] == "yc"
    assert float(row["score"]) >= 1
    assert row["signals"]["hiring"] == 1
    assert row["signals"]["scaling"] == 1


def test_companies_enrich_endpoint(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    # seed one company
    seed = client.post(
        _api("/companies/ingest"),
        headers=hdr,
        json={"source": "manual", "companies": [{"company_name": "Acme", "website": "https://acme.com"}]},
    )
    assert seed.status_code == 200, seed.text
    listed = client.get(_api("/companies"), headers=hdr)
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert rows
    acme = next((x for x in rows if x.get("domain") == "acme.com"), None)
    assert acme is not None
    cid = int(acme["id"])

    from backend.enrichment.website import WebsiteEnrichmentResult

    fake = WebsiteEnrichmentResult(
        url="https://acme.com",
        final_url="https://acme.com/",
        ok=True,
        has_blog=True,
        is_hiring=False,
        text_sample="Acme homepage content",
    )
    with patch("backend.services.company_enrichment_service.fetch_website_enrichment", return_value=fake):
        enr = client.post(
            _api("/companies/enrich"),
            headers=hdr,
            json={"company_ids": [cid], "limit": 20, "timeout_seconds": 8.0, "delay_seconds": 0.1},
        )
    assert enr.status_code == 200, enr.text
    assert enr.json()["ok"] is True

    get_enr = client.get(_api(f"/companies/{cid}/enrichment"), headers=hdr)
    assert get_enr.status_code == 200, get_enr.text
    body = get_enr.json()
    assert body["company_id"] == cid
    assert body["has_blog"] is True
    assert body["has_careers"] is False


def test_company_lead_candidates_and_manual_conversion(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    # Seed one company + enrichment score
    seed = client.post(
        _api("/companies/ingest"),
        headers=hdr,
        json={"source": "manual", "companies": [{"company_name": "Leadify", "website": "https://leadify.ai"}]},
    )
    assert seed.status_code == 200, seed.text

    from backend.enrichment.website import WebsiteEnrichmentResult

    fake = WebsiteEnrichmentResult(
        url="https://leadify.ai",
        final_url="https://leadify.ai/",
        ok=True,
        has_blog=False,
        is_hiring=True,
        text_sample="Leadify is expanding and hiring across GTM.",
        ads_presence=False,
    )
    with patch("backend.services.company_enrichment_service.fetch_website_enrichment", return_value=fake):
        enr = client.post(_api("/companies/enrich"), headers=hdr, json={"limit": 20})
    assert enr.status_code == 200, enr.text

    cand = client.post(
        _api("/companies/lead-candidates"),
        headers=hdr,
        json={"min_score": 1, "limit": 25, "require_priority": "any"},
    )
    assert cand.status_code == 200, cand.text
    rows = cand.json()["items"]
    assert rows
    company_id = int(rows[0]["company_id"])

    with patch(
        "backend.app.routes.companies.session_info_dict",
        return_value={"has_cache": True, "within_policy": True, "policy_days": 7},
    ):
        cr = client.post(
            _api("/companies/linkedin/create-lead"),
            headers=hdr,
            json={
                "company_id": company_id,
                "name": "Aman Verma",
                "role": "Founder",
                "profile_link": "https://www.linkedin.com/in/aman-verma-123456",
                "require_fresh_session": True,
            },
        )
    assert cr.status_code == 200, cr.text
    body = cr.json()
    assert body["ok"] is True
    assert body["lead_id"]


def test_company_to_lead_requires_manual_login_when_session_expired(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    seed = client.post(
        _api("/companies/ingest"),
        headers=hdr,
        json={"source": "manual", "companies": [{"company_name": "ExpireCo", "website": "https://expireco.io"}]},
    )
    assert seed.status_code == 200, seed.text
    listed = client.get(_api("/companies"), headers=hdr)
    assert listed.status_code == 200, listed.text
    row = next((x for x in listed.json() if x.get("domain") == "expireco.io"), None)
    assert row is not None
    company_id = int(row["id"])

    with patch(
        "backend.app.routes.companies.session_info_dict",
        return_value={"has_cache": True, "within_policy": False, "policy_days": 7},
    ):
        cr = client.post(
            _api("/companies/linkedin/create-lead"),
            headers=hdr,
            json={
                "company_id": company_id,
                "name": "Expired User",
                "role": "Founder",
                "profile_link": "https://www.linkedin.com/in/expired-user",
                "require_fresh_session": True,
            },
        )
    assert cr.status_code == 409, cr.text


def test_weekly_engine_api(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    with patch(
        "backend.services.company_weekly_engine.company_ingestion_service.collect_companies_from_source_pages",
        return_value=([], {"pages_ok": 0, "pages_failed": 0, "candidates": 0}),
    ), patch(
        "backend.services.company_weekly_engine.company_enrichment_service.enrich_companies_batch",
        return_value={"selected": 0, "ok": 0, "failed": 0, "skipped": 0},
    ):
        r = client.post(
            _api("/companies/weekly-engine/run"),
            headers=hdr,
            json={"day": "mon", "keyword": "software", "location": ""},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["day"] == "mon"
    assert "result" in body
