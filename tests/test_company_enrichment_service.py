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
        ), patch(
            "backend.services.company_enrichment_service.runtime_settings.get_ai_provider",
            return_value="none",
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
        with patch(
            "backend.services.company_enrichment_service.runtime_settings.get_ai_provider",
            return_value="none",
        ):
            stats = company_enrichment_service.enrich_companies_batch(db, limit=20)
        db.commit()
        assert stats["selected"] >= 2
        assert stats["skipped"] >= 1
    finally:
        db.close()


def test_ai_qualification_falls_back_when_ai_disabled() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        c = company_service.upsert_company(db, company_name="NoAI Co", website="https://noai.dev", source="manual")
        fake = WebsiteEnrichmentResult(
            url="https://noai.dev",
            final_url="https://noai.dev/",
            ok=True,
            has_blog=False,
            is_hiring=False,
            text_sample="NoAI Co landing page text",
            error="",
        )
        with patch("backend.services.company_enrichment_service.fetch_website_enrichment", return_value=fake), patch(
            "backend.services.company_enrichment_service.runtime_settings.get_ai_provider",
            return_value="none",
        ):
            row = company_enrichment_service.upsert_company_enrichment(db, company=c, timeout_seconds=5.0)
        db.commit()
        assert row.ai_provider == "fallback"
        assert row.ai_score >= 1
        assert bool((row.ai_summary or "").strip())
        assert len([x for x in str(row.ai_problems or "").split("\n") if x.strip()]) == 3
    finally:
        db.close()


def test_ai_qualification_uses_cache_to_avoid_duplicate_calls() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        c = company_service.upsert_company(db, company_name="Cache Co", website="https://cache.dev", source="manual")
        fake = WebsiteEnrichmentResult(
            url="https://cache.dev",
            final_url="https://cache.dev/",
            ok=True,
            has_blog=False,
            is_hiring=True,
            text_sample="Cache Co is hiring fast",
            error="",
        )
        with patch("backend.services.company_enrichment_service.fetch_website_enrichment", return_value=fake), patch(
            "backend.services.company_enrichment_service.runtime_settings.get_ai_provider",
            return_value="external_api",
        ), patch(
            "backend.services.company_enrichment_service.runtime_settings.get_external_api_key",
            return_value="test-key",
        ), patch(
            "backend.services.company_enrichment_service.external_llm_service.chat_completion_json",
            return_value='{"company_summary":"Cache summary","problems":["p1","p2","p3"],"opportunity_insight":"opp","ai_score":77}',
        ) as mocked_llm:
            row1 = company_enrichment_service.upsert_company_enrichment(db, company=c, timeout_seconds=5.0)
            row2 = company_enrichment_service.upsert_company_enrichment(db, company=c, timeout_seconds=5.0)
        db.commit()
        assert row1.ai_score == row2.ai_score
        assert mocked_llm.call_count == 1
    finally:
        db.close()


def test_ai_qualification_retries_and_falls_back_without_pipeline_break() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        c = company_service.upsert_company(db, company_name="Retry Co", website="https://retry.dev", source="manual")
        fake = WebsiteEnrichmentResult(
            url="https://retry.dev",
            final_url="https://retry.dev/",
            ok=True,
            has_blog=True,
            is_hiring=False,
            text_sample="Retry Co text",
            error="",
        )
        with patch("backend.services.company_enrichment_service.fetch_website_enrichment", return_value=fake), patch(
            "backend.services.company_enrichment_service.runtime_settings.get_ai_provider",
            return_value="external_api",
        ), patch(
            "backend.services.company_enrichment_service.runtime_settings.get_external_api_key",
            return_value="test-key",
        ), patch(
            "backend.services.company_enrichment_service.external_llm_service.chat_completion_json",
            side_effect=RuntimeError("api down"),
        ):
            row = company_enrichment_service.upsert_company_enrichment(db, company=c, timeout_seconds=5.0)
        db.commit()
        assert row.fetch_ok == 1
        assert row.ai_provider == "fallback"
        assert row.ai_score >= 1
        assert bool((row.ai_summary or "").strip())
    finally:
        db.close()
