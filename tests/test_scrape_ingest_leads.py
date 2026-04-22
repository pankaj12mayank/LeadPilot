from __future__ import annotations

from database.orm.bootstrap import get_session_factory, init_sa_tables
from backend.services import lead_orm_service


def test_ingest_scrape_rows_into_leads_dedupes():
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        rows = [
            {"full_name": "One", "linkedin_url": "https://www.linkedin.com/in/person-a", "search_keyword": "ceo"},
            {"full_name": "Two", "linkedin_url": "https://www.linkedin.com/in/person-b", "title": "VP"},
            {"full_name": "Dup", "linkedin_url": "https://www.linkedin.com/in/person-a/", "title": "Again"},
        ]
        st = lead_orm_service.ingest_scrape_rows_into_leads(db, platform="linkedin", rows=rows)
        db.commit()
        assert st["ingested_leads"] == 2
        assert st["skipped"] == 1
        assert lead_orm_service.count_leads_filtered(db) == 2
    finally:
        db.close()
