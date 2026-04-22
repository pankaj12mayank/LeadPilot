from __future__ import annotations

from typing import Any, Dict, List, Optional

import config
from backend.settings.lead_schema import LEAD_COLUMNS, normalize_lead_row, row_for_write, utc_now_iso
from backend.storage.base_storage import BaseStorage

try:
    import psycopg2
except ImportError:  # pragma: no cover - optional dependency
    psycopg2 = None  # type: ignore


_DDL = """
CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    company TEXT,
    platform TEXT,
    profile_url TEXT,
    location TEXT,
    notes TEXT,
    subject TEXT,
    message TEXT,
    score DOUBLE PRECISION DEFAULT 0,
    tier TEXT,
    status TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_platform ON leads(platform);
"""


class PostgresStorage(BaseStorage):
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or getattr(config, "POSTGRES_DSN", "") or ""

    def _connect(self):
        if psycopg2 is None:
            raise RuntimeError(
                "Postgres storage requires psycopg2-binary. Install it or set STORAGE_MODE to csv/sqlite."
            )
        if not self.dsn:
            raise RuntimeError("POSTGRES_DSN is not set.")
        return psycopg2.connect(self.dsn)

    def init_storage(self) -> None:
        with self._connect() as cx:
            with cx.cursor() as cur:
                cur.execute(_DDL)
            cx.commit()

    def create_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        self.init_storage()
        row = row_for_write(lead)
        now = utc_now_iso()
        if not row.get("created_at"):
            row["created_at"] = now
        row["updated_at"] = now
        cols = ", ".join(LEAD_COLUMNS)
        placeholders = ", ".join(["%s"] * len(LEAD_COLUMNS))
        with self._connect() as cx:
            with cx.cursor() as cur:
                cur.execute(
                    f"INSERT INTO leads ({cols}) VALUES ({placeholders})",
                    tuple(row[c] for c in LEAD_COLUMNS),
                )
            cx.commit()
        return normalize_lead_row(row)

    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        self.init_storage()
        with self._connect() as cx:
            with cx.cursor() as cur:
                cur.execute("SELECT * FROM leads WHERE lead_id = %s", (lead_id,))
                rec = cur.fetchone()
                if not rec:
                    return None
                cols = [d[0] for d in cur.description]
                return normalize_lead_row(dict(zip(cols, rec)))

    def list_leads(self) -> List[Dict[str, Any]]:
        self.init_storage()
        with self._connect() as cx:
            with cx.cursor() as cur:
                cur.execute("SELECT * FROM leads ORDER BY created_at ASC")
                cols = [d[0] for d in cur.description]
                return [normalize_lead_row(dict(zip(cols, row))) for row in cur.fetchall()]

    def update_lead(self, lead_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = self.get_lead(lead_id)
        if not current:
            return None
        merged = dict(current)
        for k, v in patch.items():
            if k in LEAD_COLUMNS and k != "lead_id":
                merged[k] = v
        merged["updated_at"] = utc_now_iso()
        row = row_for_write(merged)
        update_cols = [c for c in LEAD_COLUMNS if c != "lead_id"]
        sets = ", ".join(f"{c} = %s" for c in update_cols)
        vals = [row[c] for c in update_cols] + [lead_id]
        with self._connect() as cx:
            with cx.cursor() as cur:
                cur.execute(f"UPDATE leads SET {sets} WHERE lead_id = %s", vals)
            cx.commit()
        return self.get_lead(lead_id)

    def delete_lead(self, lead_id: str) -> bool:
        self.init_storage()
        with self._connect() as cx:
            with cx.cursor() as cur:
                cur.execute("DELETE FROM leads WHERE lead_id = %s", (lead_id,))
                n = cur.rowcount
            cx.commit()
            return n > 0

    def update_status(self, lead_id: str, status: str) -> Optional[Dict[str, Any]]:
        return self.update_lead(lead_id, {"status": status})

    def sync_leads(self, leads: List[Dict[str, Any]]) -> None:
        self.init_storage()
        rows = [row_for_write(x) for x in leads]
        now = utc_now_iso()
        for r in rows:
            if not r.get("created_at"):
                r["created_at"] = now
            r["updated_at"] = now
        cols = ", ".join(LEAD_COLUMNS)
        placeholders = ", ".join(["%s"] * len(LEAD_COLUMNS))
        with self._connect() as cx:
            with cx.cursor() as cur:
                cur.execute("DELETE FROM leads")
                cur.executemany(
                    f"INSERT INTO leads ({cols}) VALUES ({placeholders})",
                    [tuple(r[c] for c in LEAD_COLUMNS) for r in rows],
                )
            cx.commit()
