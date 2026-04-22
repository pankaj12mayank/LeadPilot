from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List

from sqlalchemy.orm import Session

import config as app_config
from database.orm.bootstrap import get_session_factory
from database.orm.models import RawScrapeRecord
from backend.services import analytics_service, lead_orm_service
from backend.settings.lead_schema import utc_now_iso


class RawLeadSaver:
    """Persist raw dict rows to SQLite (``raw_scrape_records``) and a CSV snapshot under ``exports/``."""

    def __init__(self, db: Session | None = None) -> None:
        self._external_db = db
        self._owns_session = db is None

    def _session(self) -> Session:
        if self._external_db is not None:
            return self._external_db
        return get_session_factory()()

    def save_run(
        self,
        *,
        run_id: str,
        platform: str,
        keyword: str,
        country: str,
        industry: str,
        company_size: str,
        rows: List[Dict[str, Any]],
    ) -> str:
        app_config.ensure_data_dirs()
        now = utc_now_iso()
        db = self._session()
        csv_name = f"raw_scrape_{platform}_{run_id}.csv"
        csv_path = os.path.join(app_config.EXPORTS_DIR, csv_name)
        try:
            for row in rows:
                rec = RawScrapeRecord(
                    run_id=run_id,
                    platform=platform,
                    keyword=keyword[:512],
                    country=country[:128],
                    industry=industry[:128],
                    company_size=company_size[:64],
                    raw_json=json.dumps(row, ensure_ascii=False, default=str),
                    source_url=str(row.get("url") or row.get("source_url") or "")[:4000],
                    created_at=now,
                )
                db.add(rec)
            lead_orm_service.ingest_scrape_rows_into_leads(db, platform=platform, rows=rows)
            if self._owns_session:
                db.commit()
            else:
                db.flush()
        except Exception:
            if self._owns_session:
                db.rollback()
            raise
        else:
            try:
                analytics_service.invalidate_analytics_cache()
            except Exception:
                pass
        finally:
            if self._owns_session:
                db.close()
        from backend.scraper.csv_exporter import export_raw_rows_to_csv

        export_raw_rows_to_csv(rows, csv_path)
        return os.path.abspath(csv_path)

    @staticmethod
    def new_run_id() -> str:
        return str(uuid.uuid4())
