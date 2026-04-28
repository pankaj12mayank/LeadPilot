from __future__ import annotations

from unittest.mock import patch

from database.orm.bootstrap import get_session_factory, init_sa_tables
from backend.services import company_service, company_weekly_engine


def test_weekly_engine_mon_runs_ingest_enrich() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        with patch(
            "backend.services.company_weekly_engine.company_ingestion_service.collect_companies_from_source_pages",
            return_value=([{"company_name": "Acme", "website": "https://acme.com", "source": "yc"}], {"pages_ok": 1, "pages_failed": 0, "candidates": 1}),
        ), patch(
            "backend.services.company_weekly_engine.company_enrichment_service.enrich_companies_batch",
            return_value={"selected": 1, "ok": 1, "failed": 0, "skipped": 0},
        ):
            out = company_weekly_engine.run_weekly_engine(db, day="mon", keyword="acme", location="")
        assert out["day"] == "mon"
        assert out["result"]["saved_total"]["created"] >= 1
    finally:
        db.close()


def test_weekly_engine_saturday_manual_candidates() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        c = company_service.upsert_company(db, company_name="SatCo", website="https://satco.ai", source="manual")
        # fake enrichment row via service patch
        from backend.enrichment.website import WebsiteEnrichmentResult
        from backend.services import company_enrichment_service

        fake = WebsiteEnrichmentResult(
            url="https://satco.ai",
            final_url="https://satco.ai",
            ok=True,
            is_hiring=True,
            has_blog=False,
            ads_presence=False,
            text_sample="SatCo is hiring and growing",
        )
        with patch("backend.services.company_enrichment_service.fetch_website_enrichment", return_value=fake):
            company_enrichment_service.upsert_company_enrichment(db, company=c, timeout_seconds=5.0)
        db.commit()

        with patch(
            "backend.services.company_weekly_engine.session_info_dict",
            return_value={"has_cache": True, "within_policy": False, "policy_days": 7},
        ):
            out = company_weekly_engine.run_weekly_engine(db, day="sat", saturday_min_score=1, saturday_limit=20)
        assert out["day"] == "sat"
        assert out["result"]["requires_manual_login"] is True
        assert out["result"]["paused"] is True
        assert "instructions" in out["result"]
    finally:
        db.close()


def test_weekly_engine_sunday_cleanup_reporting() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        out = company_weekly_engine.run_weekly_engine(db, day="sun")
        assert out["day"] == "sun"
        rep = out["result"]
        assert "total_companies" in rep
        assert "enriched_total" in rep
        assert "high_priority_companies" in rep
    finally:
        db.close()
