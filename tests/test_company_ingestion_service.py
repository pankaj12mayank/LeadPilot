from __future__ import annotations

from backend.services import company_ingestion_service


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
