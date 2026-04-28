from __future__ import annotations

from unittest.mock import patch

from database.orm.bootstrap import get_session_factory, init_sa_tables
from backend.enrichment.website import WebsiteEnrichmentResult
from backend.services import company_enrichment_service, company_service


def test_upsert_company_enrichment_success() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        c = company_service.upsert_company(db, company_name="Acme", website="https://acme.com", source="manual")
        fake = WebsiteEnrichmentResult(
            url="https://acme.com",
            final_url="https://acme.com/",
            ok=True,
            has_blog=True,
            is_hiring=True,
            text_sample="Acme builds tooling.",
            error="",
        )
        with patch(
            "backend.services.company_enrichment_service.fetch_website_enrichment",
            return_value=fake,
        ):
            row = company_enrichment_service.upsert_company_enrichment(db, company=c, timeout_seconds=5.0)
        db.commit()
        assert row.company_id == c.id
        assert row.fetch_ok == 1
        assert row.has_blog == 1
        assert row.has_careers == 1
        assert "Acme builds" in row.content_text
        assert row.signal_hiring == 1
        assert row.score > 0
        assert row.priority in ("Hot", "Warm", "Cold")
    finally:
        db.close()


def test_enrich_companies_batch_handles_missing_website() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        company_service.upsert_company(db, company_name="NoSite", website="https://nosite.dev", source="manual")
        c2 = company_service.upsert_company(db, company_name="Blank", website="https://blank.dev", source="manual")
        c2.website = ""
        db.flush()
        stats = company_enrichment_service.enrich_companies_batch(db, limit=20)
        db.commit()
        assert stats["selected"] >= 2
        assert stats["skipped"] >= 1
    finally:
        db.close()
