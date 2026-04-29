from __future__ import annotations

from unittest.mock import patch

from backend.services import company_ingestion_service, company_service
from database.orm.bootstrap import get_session_factory, init_sa_tables


def test_collect_companies_from_source_pages_extracts_and_dedupes():
    html = """
    <html><body>
      <a href="https://acme.com">Acme Inc</a>
      <a href="https://www.beta.io/about">Beta</a>
      <a href="https://acme.com/careers">Acme Careers</a>
      <a href="https://linkedin.com/company/acme">LinkedIn</a>
    </body></html>
    """

    def fake_fetch(_url: str) -> str:
        return html

    rows, stats = company_ingestion_service.collect_companies_from_source_pages(
        source="yc",
        seed_urls=["https://example.com/dir"],
        batch_size=10,
        delay_seconds=0.2,
        max_companies=100,
        fetch_html=fake_fetch,
    )
    assert stats["pages_ok"] == 1
    assert stats["pages_failed"] == 0
    assert len(rows) == 2
    domains = sorted([r["website"] for r in rows])
    assert domains == ["https://acme.com", "https://beta.io"]
    assert all(r["source"] == "yc" for r in rows)


def test_collect_companies_from_source_pages_unsupported_source():
    try:
        company_ingestion_service.collect_companies_from_source_pages(
            source="random",
            seed_urls=[],
        )
    except ValueError as e:
        assert "Unsupported source" in str(e)
    else:
        raise AssertionError("Expected ValueError for unsupported source")


def test_ingest_from_sources_aggregates_and_delays_between_sources():
    with (
        patch(
            "backend.services.company_ingestion_service.ingest_from_source",
            side_effect=[
                {
                    "fetched": {"pages_ok": 1, "pages_failed": 0, "candidates": 2},
                    "saved": {"created": 2, "updated": 0, "skipped": 0},
                },
                {
                    "fetched": {"pages_ok": 2, "pages_failed": 1, "candidates": 3},
                    "saved": {"created": 1, "updated": 1, "skipped": 1},
                },
            ],
        ) as mocked_ingest,
        patch("backend.services.company_ingestion_service.time.sleep") as mocked_sleep,
    ):
        result = company_ingestion_service.ingest_from_sources(
            db=None,
            sources=["yc", "job_board"],
            shared_source_input={"batch_size": 10},
            delay_between_sources=0.5,
        )

    assert result["sources"] == ["yc", "job_board"]
    assert result["fetched_total"] == {"pages_ok": 3, "pages_failed": 1, "candidates": 5}
    assert result["saved_total"] == {"created": 3, "updated": 1, "skipped": 1}
    assert [run["source"] for run in result["runs"]] == ["yc", "job_board"]
    assert mocked_ingest.call_count == 2
    mocked_sleep.assert_called_once_with(0.5)


def test_run_source_supports_custom_registry_source_via_generic_adapter():
    html = """
    <html><body>
      <a href="https://customco.dev">Custom Co</a>
    </body></html>
    """

    def fake_fetch(_url: str) -> str:
        return html

    with patch(
        "backend.services.company_ingestion_service.runtime_settings.get_source_registry_entry",
        return_value={
            "source_name": "custom_directory",
            "source_type": "directory",
            "enabled": True,
            "input_type": "url",
            "adapter_function": "collect_companies_from_source_pages",
        },
    ):
        rows = company_ingestion_service.run_source(
            "custom_directory",
            {
                "seed_urls": ["https://example.com/custom-list"],
                "batch_size": 10,
                "delay_seconds": 0.2,
                "max_companies": 10,
                "fetch_html": fake_fetch,
            },
        )

    assert rows == [{"company_name": "Custom Co", "website": "https://customco.dev", "source": "custom_directory"}]


def test_quality_filters_skip_missing_invalid_and_duplicate_domains():
    rows, stats = company_ingestion_service._apply_quality_filters(  # noqa: SLF001
        [
            {"company_name": "No website", "website": ""},
            {"company_name": "Bad link", "website": "notaurl"},
            {"company_name": "Valid Co", "website": "https://validco.com"},
            {"company_name": "Valid Co duplicate", "website": "https://www.validco.com/about"},
        ],
        source="yc",
    )
    assert rows == [{"company_name": "Valid Co", "website": "https://validco.com", "source": "yc"}]
    assert stats["missing_website"] >= 1
    assert stats["invalid_url"] >= 1
    assert stats["duplicate_domain"] >= 1


def test_quality_filters_apply_optional_min_content_length():
    rows, stats = company_ingestion_service.collect_companies_from_source_pages(
        source="yc",
        seed_urls=["https://example.com/dir"],
        batch_size=10,
        delay_seconds=0.2,
        max_companies=100,
        min_content_length=10,
        fetch_html=lambda _url: """
        <html><body>
          <a href="https://tiny.io">Tiny</a>
          <a href="https://longname.ai">Long Named Company</a>
        </body></html>
        """,
    )

    assert rows == [{"company_name": "Long Named Company", "website": "https://longname.ai", "source": "yc"}]
    assert stats["short_content"] >= 1


def test_each_source_adapter_can_extract_and_insert_into_db():
    source_cases = [
        (
            "yc",
            {
                "seed_urls": ["https://www.ycombinator.com/companies?query=ai"],
                "batch_size": 2,
                "delay_seconds": 0.2,
                "max_companies": 10,
                "fetch_html": lambda _url: """
                <html><body>
                  <div class="company-card"><a href="https://www.sourcealpha.com">Source Alpha</a></div>
                </body></html>
                """,
            },
            "sourcealpha.com",
        ),
        (
            "job_board",
            {
                "keyword": "python",
                "location": "Remote",
                "batch_size": 2,
                "delay_seconds": 0.2,
                "max_companies": 10,
                "fetch_html": lambda url: {
                    "https://wellfound.com/discover/companies?query=python+Remote": """
                    <html><body><div class="company-name">Hiring Source</div></body></html>
                    """,
                    "https://www.indeed.com/companies/search?q=python+Remote": "<html><body></body></html>",
                    "https://www.google.com/search?q=Hiring+Source+official+site": """
                    <html><body><a href="https://hiringsource.dev">Hiring Source</a></body></html>
                    """,
                }[url],
            },
            "hiringsource.dev",
        ),
        (
            "local",
            {
                "keyword": "dentist",
                "location": "Pune",
                "batch_size": 2,
                "delay_seconds": 0.2,
                "max_companies": 10,
                "fetch_html": lambda _url: """
                <html><body>
                  <div class="business-card"><a href="https://localcare.in">Local Care</a></div>
                </body></html>
                """,
            },
            "localcare.in",
        ),
    ]

    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        for source, source_input, expected_domain in source_cases:
            rows = company_ingestion_service.run_source(source, source_input)
            assert rows, f"{source} should extract at least one row"
            assert all(str(row.get("website") or "").startswith("https://") for row in rows)

            stats = company_service.ingest_public_companies(db, rows, default_source=source)
            assert int(stats["created"]) >= 1

            saved = company_service.get_company_by_domain(db, expected_domain)
            assert saved is not None
            assert saved.domain == expected_domain
            assert str(saved.source or "") == source
    finally:
        db.close()


def test_source_adapters_do_not_crash_on_sparse_input():
    sparse_pages = {
        "yc": {"seed_urls": ["https://example.com/yc"], "fetch_html": lambda _url: "<html><body></body></html>"},
        "job_board": {
            "keyword": "python",
            "location": "Remote",
            "fetch_html": lambda _url: "<html><body></body></html>",
        },
        "local": {
            "keyword": "dentist",
            "location": "Pune",
            "fetch_html": lambda _url: "<html><body></body></html>",
        },
    }

    for source, source_input in sparse_pages.items():
        rows = company_ingestion_service.run_source(
            source,
            {
                "batch_size": 2,
                "delay_seconds": 0.2,
                "max_companies": 5,
                **source_input,
            },
        )
        assert rows == []
