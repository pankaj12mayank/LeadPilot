from __future__ import annotations

from sqlalchemy import delete

from database.orm.bootstrap import get_session_factory, init_sa_tables
from database.orm.models import Company
from backend.services import company_service


def _reset_companies(db) -> None:
    db.execute(delete(Company))
    db.commit()


def test_normalize_company_domain() -> None:
    assert company_service.normalize_company_domain("https://www.Acme.com/about") == "acme.com"
    assert company_service.normalize_company_domain("WWW.ACME.COM") == "acme.com"
    assert company_service.normalize_company_domain("acme.com/path?q=1") == "acme.com"
    assert company_service.normalize_company_domain("") == ""


def test_normalize_company_source() -> None:
    assert company_service.normalize_company_source("job_board") == "job_board"
    assert company_service.normalize_company_source("Job Board") == "job_board"
    assert company_service.normalize_company_source("yc") == "yc"
    assert company_service.normalize_company_source("LOCAL") == "local"
    assert company_service.normalize_company_source("other") == "manual"
    assert company_service.normalize_company_source("") == "manual"


def test_upsert_company_dedupes_by_domain() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        _reset_companies(db)
        one = company_service.upsert_company(
            db,
            company_name="Acme Inc",
            website="https://www.acme.com",
            source="linkedin",
        )
        first_seen = one.first_seen
        two = company_service.upsert_company(
            db,
            company_name="Acme Updated",
            website="http://acme.com/about",
            source="manual",
        )
        db.commit()

        assert one.id == two.id
        assert two.domain == "acme.com"
        assert two.company_name == "Acme Updated"
        assert two.source == "linkedin,manual"
        assert two.first_seen == first_seen
        assert company_service.get_company_by_domain(db, "https://acme.com") is not None
        assert len(company_service.list_companies(db)) == 1
    finally:
        db.close()


def test_create_company_requires_domain() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        _reset_companies(db)
        try:
            company_service.create_company(db, company_name="Bad", website="", source="test")
        except ValueError as e:
            assert "website/domain" in str(e)
        else:
            raise AssertionError("Expected ValueError for invalid website/domain")
    finally:
        db.close()


def test_ingest_public_companies_stats() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        _reset_companies(db)
        stats1 = company_service.ingest_public_companies(
            db,
            [
                {"company_name": "Acme", "website": "https://acme.com", "source": "mock"},
                {"company_name": "Beta", "domain": "beta.io"},
                {"company_name": "", "website": "missing-name.com"},
            ],
            default_source="manual",
        )
        db.commit()
        assert stats1 == {"created": 2, "updated": 0, "skipped": 1}

        stats2 = company_service.ingest_public_companies(
            db,
            [{"company_name": "Acme 2", "website": "http://www.acme.com/about", "source": "refresh"}],
            default_source="manual",
        )
        db.commit()
        row = company_service.get_company_by_domain(db, "acme.com")
        assert row is not None
        assert row.company_name == "Acme 2"
        assert row.source == "manual"
        assert stats2 == {"created": 0, "updated": 1, "skipped": 0}
    finally:
        db.close()


def test_upsert_company_persists_signals_and_ai_score() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        _reset_companies(db)
        row = company_service.upsert_company(
            db,
            company_name="Signal Co",
            website="https://signalco.ai",
            source="yc",
            signals={"hiring": True, "ads_gap": True},
            ai_score=88,
        )
        db.commit()
        assert row.signals == "hiring,ads_gap"
        assert float(row.ai_score) == 88.0
    finally:
        db.close()


def test_create_company_normalizes_source_to_allowed_set() -> None:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        _reset_companies(db)
        row = company_service.create_company(
            db,
            company_name="Gamma",
            website="https://gamma.dev",
            source="random_source",
        )
        db.commit()
        assert row.source == "manual"
    finally:
        db.close()
