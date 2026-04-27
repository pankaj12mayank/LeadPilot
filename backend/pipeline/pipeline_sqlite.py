from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import config as app_config


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_pipeline_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS raw_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            full_name TEXT,
            title TEXT,
            company_name TEXT,
            location TEXT,
            linkedin_url TEXT,
            row_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS enriched_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            full_name TEXT,
            title TEXT,
            company_name TEXT,
            location TEXT,
            linkedin_url TEXT,
            company_website TEXT,
            score REAL,
            category TEXT,
            company_summary TEXT,
            pain_points TEXT,
            opportunity_insight TEXT,
            linkedin_message TEXT,
            email_message TEXT,
            followup_message TEXT,
            row_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS outreach_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            lead_key TEXT,
            full_name TEXT,
            linkedin_url TEXT,
            primary_message TEXT,
            email_message TEXT,
            followup_message TEXT,
            status TEXT NOT NULL DEFAULT 'New',
            row_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )


def save_pipeline_run(
    *,
    run_id: str,
    raw_rows: List[Dict[str, Any]],
    enriched_rows: List[Dict[str, Any]],
    queue_rows: List[Dict[str, Any]],
) -> str:
    """Append one pipeline run to SQLite (same DB file as app config, new tables)."""
    app_config.ensure_data_dirs()
    path = os.path.abspath(app_config.SQLITE_DB_PATH)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        ensure_pipeline_schema(conn)
        now = _now_iso()
        cur = conn.cursor()
        for r in raw_rows:
            cur.execute(
                """
                INSERT INTO raw_leads
                (run_id, full_name, title, company_name, location, linkedin_url, row_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    str(r.get("name") or r.get("full_name") or ""),
                    str(r.get("title") or ""),
                    str(r.get("company") or r.get("company_name") or ""),
                    str(r.get("location") or ""),
                    str(r.get("linkedin_url") or ""),
                    json.dumps(r, ensure_ascii=False, default=str),
                    now,
                ),
            )
        for r in enriched_rows:
            cur.execute(
                """
                INSERT INTO enriched_leads (
                    run_id, full_name, title, company_name, location, linkedin_url, company_website,
                    score, category, company_summary, pain_points, opportunity_insight,
                    linkedin_message, email_message, followup_message, row_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    str(r.get("name") or r.get("full_name") or ""),
                    str(r.get("title") or ""),
                    str(r.get("company") or r.get("company_name") or ""),
                    str(r.get("location") or ""),
                    str(r.get("linkedin_url") or ""),
                    str(r.get("website") or r.get("company_website") or ""),
                    float(r.get("score") or 0) if r.get("score") is not None else None,
                    str(r.get("category") or ""),
                    str(r.get("company_summary") or r.get("short_summary") or ""),
                    str(r.get("pain_points") or ""),
                    str(r.get("opportunity_insight") or ""),
                    str(r.get("linkedin_message") or ""),
                    str(r.get("email_message") or ""),
                    str(r.get("followup_message") or ""),
                    json.dumps(r, ensure_ascii=False, default=str),
                    now,
                ),
            )
        for r in queue_rows:
            st = str(r.get("status") or "New").strip() or "New"
            cur.execute(
                """
                INSERT INTO outreach_queue (
                    run_id, lead_key, full_name, linkedin_url, primary_message, email_message,
                    followup_message, status, row_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    str(r.get("lead_key") or r.get("linkedin_url") or uuid.uuid4().hex),
                    str(r.get("name") or r.get("full_name") or ""),
                    str(r.get("linkedin_url") or ""),
                    str(r.get("message") or r.get("linkedin_message") or ""),
                    str(r.get("email_message") or ""),
                    str(r.get("followup_message") or ""),
                    st,
                    json.dumps(r, ensure_ascii=False, default=str),
                    now,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return path
