from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional

import config
from backend.settings.lead_schema import LEAD_COLUMNS, normalize_lead_row, row_for_write, utc_now_iso
from backend.storage.base_storage import BaseStorage


class SqliteStorage(BaseStorage):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or getattr(config, "SQLITE_DB_PATH", "database/leads.db")

    def _conn(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        return sqlite3.connect(self.db_path)

    def init_storage(self) -> None:
        from database.migrate import ensure_sqlite_schema

        ensure_sqlite_schema(self.db_path)

    def create_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        self.init_storage()
        row = row_for_write(lead)
        now = utc_now_iso()
        if not row.get("created_at"):
            row["created_at"] = now
        row["updated_at"] = now
        cols = ", ".join(LEAD_COLUMNS)
        placeholders = ", ".join("?" * len(LEAD_COLUMNS))
        with self._conn() as cx:
            cx.execute(
                f"INSERT INTO leads ({cols}) VALUES ({placeholders})",
                tuple(row[c] for c in LEAD_COLUMNS),
            )
        return normalize_lead_row(row)

    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        self.init_storage()
        with self._conn() as cx:
            cur = cx.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,))
            rec = cur.fetchone()
            if not rec:
                return None
            cols = [d[0] for d in cur.description]
            return normalize_lead_row(dict(zip(cols, rec)))

    def list_leads(self) -> List[Dict[str, Any]]:
        self.init_storage()
        with self._conn() as cx:
            cur = cx.execute("SELECT * FROM leads ORDER BY created_at ASC")
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
        sets = ", ".join(f"{c} = ?" for c in update_cols)
        vals = [row[c] for c in update_cols] + [lead_id]
        with self._conn() as cx:
            cx.execute(f"UPDATE leads SET {sets} WHERE lead_id = ?", vals)
        return self.get_lead(lead_id)

    def delete_lead(self, lead_id: str) -> bool:
        self.init_storage()
        with self._conn() as cx:
            cur = cx.execute("DELETE FROM leads WHERE lead_id = ?", (lead_id,))
            return cur.rowcount > 0

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
        placeholders = ", ".join("?" * len(LEAD_COLUMNS))
        with self._conn() as cx:
            cx.execute("DELETE FROM leads")
            cx.executemany(
                f"INSERT INTO leads ({cols}) VALUES ({placeholders})",
                [tuple(r[c] for c in LEAD_COLUMNS) for r in rows],
            )
