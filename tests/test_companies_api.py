from __future__ import annotations

import uuid

import config
from backend.services import company_ingestion_service, company_service


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


def test_task_classification_returns_standard_task_object(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    r = client.get(_api("/companies/task-classification"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body and isinstance(body["items"], list) and body["items"]
    row = body["items"][0]
    assert "task_type" in row
    assert "priority" in row
    assert "requires_login" in row
    assert "payload" in row


def test_task_priority_can_be_overridden_from_admin_config(client):
    from backend.app.middleware.jwt import create_access_token

    admin_hdr = {"Authorization": f"Bearer {create_access_token('admin-test', {'admin': True})}"}
    p = client.patch(
        _api("/admin/config"),
        headers=admin_hdr,
        json={"task_priority": {"linkedin": "high", "scoring": "low", "enrichment": "medium", "ingestion": "low"}},
    )
    assert p.status_code == 200, p.text

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    r = client.get(_api("/companies/task-classification"), headers=hdr)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    scoring = next((x for x in items if x.get("task_name") == "scoring"), None)
    assert scoring is not None
    assert scoring["priority"] == "low"


def test_user_config_sync_endpoint_returns_admin_config_and_event(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    r = client.get(_api("/companies/user-config"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "admin_config" in body
    cfg = body["admin_config"]
    assert "targeting" in cfg
    assert "sources" in cfg
    assert "scoring_weights" in cfg
    assert "signals_config" in cfg
    assert "scheduler_config" in cfg
    assert "session_policy" in cfg
    assert "retry_policy" in cfg
    assert "task_priority" in cfg
    assert "source_registry" in cfg
    assert any(item.get("source_name") == "job_board" for item in cfg["source_registry"])


def test_admin_config_change_propagates_to_queue_and_user_sync_payload(client):
    from unittest.mock import patch

    from backend.app.middleware.jwt import create_access_token

    admin_hdr = {"Authorization": f"Bearer {create_access_token('admin-test', {'admin': True})}"}
    token = _token(client)
    user_hdr = {"Authorization": f"Bearer {token}"}

    baseline = client.patch(
        _api("/admin/config"),
        headers=admin_hdr,
        json={
            "targeting": {
                "keywords": ["baseline"],
                "locations": ["india"],
                "industries": ["services"],
                "company_types": ["agency"],
                "preferred_locations": ["mumbai"],
                "preferred_keywords": ["baseline"],
                "min_company_score": 61,
            },
            "scoring_weights": {
                "role_weight": 40,
                "signal_weight": 35,
                "data_weight": 25,
                "company_size_weight": 20,
                "base_factor_mix": 10,
            },
            "task_priority": {
                "linkedin": "high",
                "scoring": "high",
                "enrichment": "medium",
                "ingestion": "low",
            },
        },
    )
    assert baseline.status_code == 200, baseline.text

    with patch("backend.app.main.task_queue_service.enqueue") as mocked_enqueue:
        mocked_enqueue.return_value = {
            "task_type": "scoring",
            "priority": "low",
            "requires_login": False,
            "payload": {"batch": "config_updated_scoring", "source_event": "config_updated"},
        }
        p = client.patch(
            _api("/admin/config"),
            headers=admin_hdr,
            json={
                "targeting": {
                    "keywords": ["ai agencies"],
                    "locations": ["uae"],
                    "industries": ["software"],
                    "company_types": ["startup"],
                    "preferred_locations": ["dubai"],
                    "preferred_keywords": ["agency"],
                    "min_company_score": 84,
                },
                "scoring_weights": {
                    "role_weight": 20,
                    "signal_weight": 65,
                    "data_weight": 15,
                    "company_size_weight": 18,
                    "base_factor_mix": 12,
                },
                "task_priority": {
                    "linkedin": "medium",
                    "scoring": "low",
                    "enrichment": "high",
                    "ingestion": "medium",
                },
            },
        )
    assert p.status_code == 200, p.text
    mocked_enqueue.assert_called_once()
    queued_task = mocked_enqueue.call_args.args[0]
    assert queued_task["task_type"] == "scoring"
    assert queued_task["priority"] == "low"
    assert queued_task["payload"]["source_event"] == "config_updated"

    synced = client.get(_api("/companies/user-config"), headers=user_hdr)
    assert synced.status_code == 200, synced.text
    body = synced.json()
    cfg = body["admin_config"]
    event = body["config_event"]

    assert cfg["targeting"]["keywords"] == ["ai agencies"]
    assert cfg["targeting"]["preferred_locations"] == ["dubai"]
    assert cfg["targeting"]["min_company_score"] == 84
    assert cfg["scoring_weights"]["signal_weight"] == 65
    assert cfg["task_priority"]["scoring"] == "low"
    assert cfg["task_priority"]["enrichment"] == "high"

    assert event is not None
    assert event["event"] == "config_updated"
    assert event["timestamp"]
    assert "admin_config.scoring_weights.signal_weight" in event["changed_fields"]
    assert "admin_config.targeting.min_company_score" in event["changed_fields"]
    assert "admin_config.task_priority.enrichment" in event["changed_fields"]


def test_explorer_respects_admin_enabled_sources_and_signals(client):
    from backend.app.middleware.jwt import create_access_token

    admin_hdr = {"Authorization": f"Bearer {create_access_token('admin-test', {'admin': True})}"}
    p = client.patch(
        _api("/admin/config"),
        headers=admin_hdr,
        json={
            "sources": {
                "job_boards": True,
                "startup_directories": True,
                "local_listings": True,
                "manual_seeds": True,
                "allowed_sources": ["yc"],
            },
            "signals_config": {"hiring_enabled": True, "scaling_enabled": False},
        },
    )
    assert p.status_code == 200, p.text

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    r = client.post(
        _api("/companies/explorer/search"),
        headers=hdr,
        json={
            "mode": "explorer",
            "keyword": "saas",
            "source_filter": "job_board",
            "signal_hiring": True,
            "signal_scaling": True,
            "min_results": 1,
            "max_results": 10,
            "sources": ["yc", "job_board", "local"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    eff = body.get("effective_filters") or {}
    assert eff.get("source_filter") == "all"
    assert eff.get("signal_hiring") is True
    assert eff.get("signal_scaling") is False
    assert "yc" in (eff.get("enabled_sources") or [])
    assert "job_board" not in (eff.get("enabled_sources") or [])
    ingest = body.get("ingestion") or {}
    assert ingest.get("effective_sources") == ["yc"]


def test_companies_ingest_real_sources(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    fake_candidates = [
        {"company_name": "Yc One", "website": "https://yc-one.com", "source": "yc"},
        {"company_name": "Yc Two", "website": "https://yc-two.dev", "source": "yc"},
    ]
    with patch(
        "backend.app.routes.companies.company_ingestion_service.run_source",
        return_value=fake_candidates,
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


def test_ingest_real_connects_adapter_to_company_db_upsert_flow(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    with patch(
        "backend.app.routes.companies.company_ingestion_service.run_source",
        return_value=[
            {"company_name": "Flow Co", "website": "https://flowco.ai", "source": "job_board"},
        ],
    ):
        first = client.post(
            _api("/companies/ingest-real"),
            headers=hdr,
            json={
                "source": "job_board",
                "seed_urls": ["https://wellfound.com/discover/companies?query=flow"],
                "batch_size": 10,
                "delay_seconds": 0.2,
                "max_companies": 50,
                "enrich_after_ingest": False,
            },
        )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["saved"]["created"] == 1
    assert first_body["saved"]["updated"] == 0

    with patch(
        "backend.app.routes.companies.company_ingestion_service.run_source",
        return_value=[
            {"company_name": "Flow Co Updated", "website": "https://www.flowco.ai/about", "source": "job_board"},
        ],
    ):
        second = client.post(
            _api("/companies/ingest-real"),
            headers=hdr,
            json={
                "source": "job_board",
                "seed_urls": ["https://www.indeed.com/companies/search?q=flow"],
                "batch_size": 10,
                "delay_seconds": 0.2,
                "max_companies": 50,
                "enrich_after_ingest": False,
            },
        )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["saved"]["created"] == 0
    assert second_body["saved"]["updated"] == 1

    row = client.get(_api("/companies/by-domain/flowco.ai"), headers=hdr)
    assert row.status_code == 200, row.text
    data = row.json()
    assert data["company_name"] == "Flow Co Updated"
    assert data["domain"] == "flowco.ai"
    assert data["source"] == "job_board"


def test_companies_ingest_real_multiple_sources_combines_runs(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    with patch(
        "backend.app.routes.companies.company_ingestion_service.ingest_from_sources",
        return_value={
            "sources": ["yc", "job_board"],
            "runs": [
                {
                    "source": "yc",
                    "fetched": {"pages_ok": 1, "pages_failed": 0, "candidates": 2},
                    "saved": {"created": 2, "updated": 0, "skipped": 0},
                },
                {
                    "source": "job_board",
                    "fetched": {"pages_ok": 2, "pages_failed": 0, "candidates": 1},
                    "saved": {"created": 1, "updated": 0, "skipped": 0},
                },
            ],
            "fetched_total": {"pages_ok": 3, "pages_failed": 0, "candidates": 3},
            "saved_total": {"created": 3, "updated": 0, "skipped": 0},
        },
    ) as mocked_ingest:
        r = client.post(
            _api("/companies/ingest-real"),
            headers=hdr,
            json={
                "source": "yc",
                "sources": ["yc", "job_board"],
                "seed_urls": ["https://www.ycombinator.com/companies"],
                "batch_size": 10,
                "delay_seconds": 0.2,
                "max_companies": 50,
                "enrich_after_ingest": False,
            },
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sources"] == ["yc", "job_board"]
    assert len(body["runs"]) == 2
    assert body["fetched"]["candidates"] == 3
    assert body["saved"]["created"] == 3
    mocked_ingest.assert_called_once()


def test_user_can_register_custom_source(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    source_name = f"startup_watch_{uuid.uuid4().hex[:8]}"

    r = client.post(
        _api("/companies/custom-sources"),
        headers=hdr,
        json={"source_name": source_name, "input_type": "url"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["source"]["source_name"] == source_name
    assert body["source"]["input_type"] == "url"
    assert body["source"]["adapter_function"] == "collect_companies_from_source_pages"

    cfg = client.get(_api("/companies/user-config"), headers=hdr)
    assert cfg.status_code == 200, cfg.text
    registry = (cfg.json().get("admin_config") or {}).get("source_registry") or []
    names = {item["source_name"] for item in registry}
    assert source_name in names


def test_custom_source_registration_rejects_duplicate_name(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    source_name = f"market_map_{uuid.uuid4().hex[:8]}"

    first = client.post(
        _api("/companies/custom-sources"),
        headers=hdr,
        json={"source_name": source_name, "input_type": "keyword"},
    )
    assert first.status_code == 200, first.text

    second = client.post(
        _api("/companies/custom-sources"),
        headers=hdr,
        json={"source_name": source_name, "input_type": "keyword"},
    )
    assert second.status_code == 400, second.text
    assert second.json()["detail"] == "Source already exists"


def test_run_source_returns_standardized_rows():
    html = """
    <html>
      <body>
        <a href="https://www.acme.com/about">Acme Inc</a>
        <a href="https://www.beta.io">Beta</a>
        <a href="/relative">Relative only</a>
        <a href="mailto:test@example.com">Email</a>
      </body>
    </html>
    """

    rows = company_ingestion_service.run_source(
        "yc",
        {
            "seed_urls": ["https://example.com/list"],
            "batch_size": 10,
            "delay_seconds": 0.2,
            "max_companies": 20,
            "fetch_html": lambda _url: html,
        },
    )

    assert rows[0]["company_name"] == "Acme Inc"
    assert rows[0]["website"] == "https://acme.com"
    assert rows[0]["source"] == "yc"
    assert any(row["website"] == "https://beta.io" for row in rows)
    assert all("website" in row and row["website"].startswith("https://") for row in rows)


def test_run_source_skips_entries_without_valid_website():
    rows = company_ingestion_service.run_source(
        "local",
        {
            "seed_urls": ["https://example.com/search"],
            "batch_size": 10,
            "delay_seconds": 0.2,
            "max_companies": 20,
            "fetch_html": lambda _url: """
                <html><body>
                  <a href="javascript:void(0)">No Site</a>
                  <a href="https://www.validco.ai/path">Valid Co</a>
                  <a href="https://linkedin.com/company/not-valid">Social</a>
                </body></html>
            """,
        },
    )

    assert rows == [
        {
            "company_name": "Valid Co",
            "website": "https://validco.ai",
            "source": "local",
        }
    ]


def test_job_board_adapter_returns_hiring_companies_from_keyword_and_location():
    pages = {
        "https://wellfound.com/discover/companies?query=python+developer+Bangalore": """
            <html><body>
              <div class="company-name">Acme Hiring</div>
              <div class="company-name">Beta Labs</div>
            </body></html>
        """,
        "https://www.indeed.com/companies/search?q=python+developer+Bangalore": """
            <html><body>
              <div class="company-name">Acme Hiring</div>
              <div class="company-name">Gamma Works</div>
            </body></html>
        """,
        "https://www.google.com/search?q=Acme+Hiring+official+site": """
            <html><body><a href="https://www.acmehiring.com">Acme Hiring</a></body></html>
        """,
        "https://www.google.com/search?q=Beta+Labs+official+site": """
            <html><body><a href="https://betalabs.ai">Beta Labs</a></body></html>
        """,
        "https://www.google.com/search?q=Gamma+Works+official+site": """
            <html><body><a href="https://gammaworks.io">Gamma Works</a></body></html>
        """,
    }

    rows = company_ingestion_service.run_source(
        "job_board",
        {
            "keyword": "python developer",
            "location": "Bangalore",
            "batch_size": 2,
            "delay_seconds": 0.2,
            "max_companies": 10,
            "fetch_html": lambda url: pages[url],
        },
    )

    assert [row["company_name"] for row in rows] == ["Acme Hiring", "Beta Labs", "Gamma Works"]
    assert [row["website"] for row in rows] == ["https://acmehiring.com", "https://betalabs.ai", "https://gammaworks.io"]
    assert all(row["source"] == "job_board" for row in rows)


def test_job_board_adapter_skips_companies_without_website_lookup():
    pages = {
        "https://wellfound.com/discover/companies?query=designer+Remote": """
            <html><body>
              <div class="company-name">No Site Co</div>
              <div class="company-name">Valid Site Co</div>
            </body></html>
        """,
        "https://www.indeed.com/companies/search?q=designer+Remote": """
            <html><body></body></html>
        """,
        "https://www.google.com/search?q=No+Site+Co+official+site": """
            <html><body><a href="https://linkedin.com/company/no-site-co">Social</a></body></html>
        """,
        "https://www.google.com/search?q=Valid+Site+Co+official+site": """
            <html><body><a href="https://www.validsite.co">Valid Site Co</a></body></html>
        """,
    }

    rows = company_ingestion_service.run_source(
        "job_board",
        {
            "keyword": "designer",
            "location": "Remote",
            "batch_size": 2,
            "delay_seconds": 0.2,
            "max_companies": 10,
            "fetch_html": lambda url: pages[url],
        },
    )

    assert rows == [
        {
            "company_name": "Valid Site Co",
            "website": "https://validsite.co",
            "source": "job_board",
        }
    ]


def test_startup_directory_adapter_extracts_startup_companies():
    rows = company_ingestion_service.run_source(
        "yc",
        {
            "seed_urls": ["https://www.ycombinator.com/companies?query=ai"],
            "batch_size": 2,
            "delay_seconds": 0.2,
            "max_companies": 10,
            "fetch_html": lambda _url: """
                <html><body>
                  <div class="company-card"><a href="https://www.startalpha.com">Start Alpha</a></div>
                  <div class="company-card"><a href="https://beta-startup.io/about">Beta Startup</a></div>
                </body></html>
            """,
        },
    )

    assert rows == [
        {"company_name": "Start Alpha", "website": "https://startalpha.com", "source": "yc"},
        {"company_name": "Beta Startup", "website": "https://beta-startup.io", "source": "yc"},
    ]


def test_startup_directory_adapter_skips_entries_without_valid_website():
    rows = company_ingestion_service.run_source(
        "crunchbase",
        {
            "seed_urls": ["https://www.crunchbase.com/discover/organization.companies"],
            "batch_size": 2,
            "delay_seconds": 0.2,
            "max_companies": 10,
            "fetch_html": lambda _url: """
                <html><body>
                  <div class="startup-card"><a href="/company/internal-page">Internal Only</a></div>
                  <div class="startup-card"><a href="https://www.validstartup.ai">Valid Startup</a></div>
                  <div class="startup-card"><a href="https://linkedin.com/company/not-valid">Social Only</a></div>
                </body></html>
            """,
        },
    )

    assert rows == [
        {"company_name": "Valid Startup", "website": "https://validstartup.ai", "source": "crunchbase"}
    ]


def test_local_business_adapter_extracts_local_companies():
    rows = company_ingestion_service.run_source(
        "local",
        {
            "keyword": "dentist",
            "location": "Mumbai",
            "batch_size": 2,
            "delay_seconds": 0.2,
            "max_companies": 10,
            "fetch_html": lambda _url: """
                <html><body>
                  <div class="business-card"><a href="https://www.citydental.in">City Dental</a></div>
                  <div class="business-card"><a href="https://smilecareclinic.com/about">Smile Care Clinic</a></div>
                </body></html>
            """,
        },
    )

    assert rows == [
        {"company_name": "City Dental", "website": "https://citydental.in", "source": "local"},
        {"company_name": "Smile Care Clinic", "website": "https://smilecareclinic.com", "source": "local"},
    ]


def test_local_business_adapter_limits_results_per_run():
    rows = company_ingestion_service.run_source(
        "local",
        {
            "keyword": "agency",
            "location": "Delhi",
            "batch_size": 2,
            "delay_seconds": 0.2,
            "max_companies": 2,
            "fetch_html": lambda _url: """
                <html><body>
                  <div class="business-card"><a href="https://alphaagency.in">Alpha Agency</a></div>
                  <div class="business-card"><a href="https://betaagency.in">Beta Agency</a></div>
                  <div class="business-card"><a href="https://gammaagency.in">Gamma Agency</a></div>
                </body></html>
            """,
        },
    )

    assert rows == [
        {"company_name": "Alpha Agency", "website": "https://alphaagency.in", "source": "local"},
        {"company_name": "Beta Agency", "website": "https://betaagency.in", "source": "local"},
    ]


def test_collect_companies_from_source_pages_uses_local_adapter():
    rows, stats = company_ingestion_service.collect_companies_from_source_pages(
        source="local",
        seed_urls=["https://www.google.com/search?q=salon+Pune+company+official+site"],
        batch_size=2,
        delay_seconds=0.2,
        max_companies=2,
        fetch_html=lambda _url: """
            <html><body>
              <div class="business-card"><a href="https://stylehub.in">Style Hub</a></div>
              <div class="business-card"><a href="https://trimzone.in">Trim Zone</a></div>
              <div class="business-card"><a href="https://extrarow.in">Extra Row</a></div>
            </body></html>
        """,
    )

    assert rows == [
        {"company_name": "Style Hub", "website": "https://stylehub.in", "source": "local"},
        {"company_name": "Trim Zone", "website": "https://trimzone.in", "source": "local"},
    ]
    assert stats["candidates"] == 2


def test_companies_explorer_search_triggers_ingest_when_low_results(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    # ensure no direct DB hits for this keyword
    listed = client.get(_api("/companies"), headers=hdr)
    assert listed.status_code == 200, listed.text

    def fake_ingest_from_sources(*, db, sources, **_kwargs):
        saved = company_service.ingest_public_companies(
            db,
            [{"company_name": "Cloud Nova", "website": "https://cloudnova.ai", "source": "yc"}],
            default_source="yc",
        )
        return {
            "sources": list(sources),
            "runs": [
                {
                    "source": "yc",
                    "fetched": {"pages_ok": 1, "pages_failed": 0, "candidates": 1},
                    "saved": saved,
                }
            ],
            "fetched_total": {"pages_ok": 1, "pages_failed": 0, "candidates": 1},
            "saved_total": saved,
        }

    with patch(
        "backend.app.routes.companies.company_ingestion_service.ingest_from_sources",
        side_effect=fake_ingest_from_sources,
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
    from backend.app.middleware.jwt import create_access_token

    admin_hdr = {"Authorization": f"Bearer {create_access_token('admin-test', {'admin': True})}"}
    cfg = client.patch(
        _api("/admin/config"),
        headers=admin_hdr,
        json={
            "sources": {
                "job_boards": True,
                "startup_directories": True,
                "local_listings": True,
                "manual_seeds": True,
                "allowed_sources": ["yc", "job_board", "local", "manual"],
            },
            "signals_config": {"hiring_enabled": True, "scaling_enabled": True},
        },
    )
    assert cfg.status_code == 200, cfg.text

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
    assert "job_log" in body
    assert body["job_log"]["job_type"] == "weekly_mon"
    assert "records_processed" in body["job_log"]
    assert "errors" in body["job_log"]
    assert "retry_next_scheduled_run" in body["job_log"]


def test_daily_auto_job_api(client):
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
            _api("/companies/daily-auto/run"),
            headers=hdr,
            json={"keyword": "software", "location": "", "batch_size": 10, "delay_seconds": 0.2},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "tasks" in body
    assert any(x.get("task_name") == "public_ingestion" for x in body["tasks"])
    assert any(x.get("task_name") == "scoring" for x in body["tasks"])
    assert "continuous_refresh" in body
    assert "retry_queue_count" in body["continuous_refresh"]
    assert "job_log" in body
    assert body["job_log"]["job_type"] == "daily_auto_job"
    assert "retry_next_scheduled_run" in body["job_log"]


def test_weekly_engine_friday_heavy_job(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    with patch(
        "backend.services.company_weekly_engine.company_enrichment_service.enrich_companies_batch",
        return_value={"selected": 0, "ok": 0, "failed": 0, "skipped": 0},
    ):
        r = client.post(
            _api("/companies/weekly-engine/run"),
            headers=hdr,
            json={"day": "fri", "keyword": "software", "location": ""},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["day"] == "fri"
    result = body["result"]
    assert result["schedule_label"] == "Weekly Heavy Refresh"
    assert "normalization" in result
    assert "dedupe" in result
    assert "refresh" in result


def test_weekly_engine_saturday_linkedin_expansion_creates_leads(client):
    from unittest.mock import patch

    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    seed = client.post(
        _api("/companies/ingest"),
        headers=hdr,
        json={"source": "manual", "companies": [{"company_name": "SatCo", "website": "https://satco.ai"}]},
    )
    assert seed.status_code == 200, seed.text
    listed = client.get(_api("/companies"), headers=hdr)
    assert listed.status_code == 200, listed.text
    row = next((x for x in listed.json() if x.get("domain") == "satco.ai"), None)
    assert row is not None
    cid = int(row["id"])

    from backend.enrichment.website import WebsiteEnrichmentResult

    fake = WebsiteEnrichmentResult(
        url="https://satco.ai",
        final_url="https://satco.ai/",
        ok=True,
        has_blog=False,
        is_hiring=True,
        text_sample="SatCo is hiring and scaling rapidly.",
    )
    with patch("backend.services.company_enrichment_service.fetch_website_enrichment", return_value=fake):
        enr = client.post(_api("/companies/enrich"), headers=hdr, json={"limit": 20})
    assert enr.status_code == 200, enr.text

    with patch(
        "backend.services.company_weekly_engine.session_info_dict",
        return_value={"has_cache": True, "within_policy": True, "policy_days": 7},
    ):
        r = client.post(
            _api("/companies/weekly-engine/run"),
            headers=hdr,
            json={
                "day": "sat",
                "saturday_min_score": 0,
                "saturday_limit": 25,
                "saturday_manual_profiles": [
                    {
                        "company_id": cid,
                        "name": "Ravi Kumar",
                        "role": "Founder",
                        "profile_link": "https://www.linkedin.com/in/ravi-kumar-satco",
                    }
                ],
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["day"] == "sat"
    assert body["result"]["paused"] is False
    assert body["result"]["conversion"]["created"] >= 1


def test_weekly_engine_sunday_report_includes_weekly_insights(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    r = client.post(
        _api("/companies/weekly-engine/run"),
        headers=hdr,
        json={"day": "sun"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["day"] == "sun"
    result = body["result"]
    assert "total_companies" in result
    assert "total_leads" in result
    assert "hot_leads" in result
    assert "report_file" in result


def test_scheduler_entrypoint_runs_by_job_type(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    r = client.post(
        _api("/companies/scheduler/run"),
        headers=hdr,
        json={"job_type": "daily_auto"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["job_type"] == "daily_auto"
    assert body["mode"] == "queue_only"
    assert body["enqueued_count"] >= 1
    assert body["queue_size"] >= 1


def test_scheduler_entrypoint_pauses_login_required_when_session_expired(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    r = client.post(
        _api("/companies/scheduler/run"),
        headers=hdr,
        json={"job_type": "saturday_linkedin"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["job_type"] == "saturday_linkedin"
    assert body["mode"] == "queue_only"
    assert body["enqueued_count"] == 1
    assert body["tasks"][0]["task_type"] == "linkedin"
    assert body["tasks"][0]["requires_login"] is True


def test_scheduler_entrypoint_skips_session_check_for_non_login_job(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}
    r = client.post(
        _api("/companies/scheduler/run"),
        headers=hdr,
        json={"job_type": "daily_auto"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["job_type"] == "daily_auto"
    assert body["mode"] == "queue_only"
    assert body["tasks"][0]["requires_login"] is False
