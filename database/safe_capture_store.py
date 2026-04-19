"""SQLite persistence for safe manual captures (stdlib ``sqlite3`` only)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def init_safe_capture_db(db_path: str | None = None) -> None:
    path = db_path or config.SAFE_CAPTURE_DB_PATH
    parent = Path(path).parent
    parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS safe_captured_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at TEXT NOT NULL,
                name TEXT,
                title TEXT,
                company TEXT,
                industry TEXT,
                location TEXT,
                website TEXT,
                email TEXT,
                source_platform TEXT,
                profile_url TEXT NOT NULL,
                score INTEGER NOT NULL,
                tier TEXT NOT NULL,
                status TEXT NOT NULL,
                enrichment_json TEXT
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_safe_leads_platform ON safe_captured_leads(source_platform);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_safe_leads_captured ON safe_captured_leads(captured_at);"
        )
        conn.commit()
    finally:
        conn.close()


def insert_captured_lead(
    lead: dict[str, Any],
    enrichment: dict[str, Any] | None,
    *,
    db_path: str | None = None,
    captured_at: str | None = None,
) -> tuple[int, str]:
    path = db_path or config.SAFE_CAPTURE_DB_PATH
    init_safe_capture_db(path)
    ts = captured_at or utc_now_iso()
    conn = sqlite3.connect(path)
    try:
        cur = conn.execute(
            """
            INSERT INTO safe_captured_leads (
                captured_at, name, title, company, industry, location, website, email,
                source_platform, profile_url, score, tier, status, enrichment_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                lead.get("name"),
                lead.get("title"),
                lead.get("company"),
                lead.get("industry"),
                lead.get("location"),
                lead.get("website"),
                lead.get("email"),
                lead.get("source_platform"),
                lead.get("profile_url"),
                int(lead.get("score") or 0),
                str(lead.get("tier") or "COLD"),
                str(lead.get("status") or "NEW"),
                json.dumps(enrichment or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cur.lastrowid or 0), ts
    finally:
        conn.close()


def fetch_all_leads(db_path: str | None = None) -> list[dict[str, Any]]:
    path = db_path or config.SAFE_CAPTURE_DB_PATH
    if not Path(path).is_file():
        return []
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM safe_captured_leads ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_lead_status(lead_id: int, status: str, *, db_path: str | None = None) -> None:
    path = db_path or config.SAFE_CAPTURE_DB_PATH
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "UPDATE safe_captured_leads SET status = ? WHERE id = ?",
            (status.strip().upper(), int(lead_id)),
        )
        conn.commit()
    finally:
        conn.close()
