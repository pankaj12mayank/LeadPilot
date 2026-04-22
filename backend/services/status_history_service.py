"""Persist lead status transitions (CRM meta DB)."""

from __future__ import annotations

from typing import Any, Dict, List

from database.meta_db import init_meta_schema, meta_connection
from backend.settings.lead_schema import utc_now_iso


def record_change(lead_id: str, old_status: str, new_status: str) -> None:
    if old_status == new_status:
        return
    init_meta_schema()
    with meta_connection() as cx:
        cx.execute(
            """
            INSERT INTO status_history (lead_id, old_status, new_status, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (lead_id, old_status or "", new_status, utc_now_iso()),
        )


def list_for_lead(lead_id: str) -> List[Dict[str, Any]]:
    init_meta_schema()
    with meta_connection() as cx:
        cur = cx.execute(
            """
            SELECT history_id, lead_id, old_status, new_status, timestamp
            FROM status_history WHERE lead_id = ? ORDER BY history_id ASC
            """,
            (lead_id,),
        )
        return [
            {
                "history_id": r["history_id"],
                "lead_id": r["lead_id"],
                "old_status": r["old_status"],
                "new_status": r["new_status"],
                "timestamp": r["timestamp"],
            }
            for r in cur.fetchall()
        ]


def list_changes_between(start_iso: str, end_iso: str) -> List[Dict[str, Any]]:
    """Status transitions with ``timestamp`` in ``[start_iso, end_iso]`` (inclusive)."""
    init_meta_schema()
    with meta_connection() as cx:
        cur = cx.execute(
            """
            SELECT history_id, lead_id, old_status, new_status, timestamp
            FROM status_history
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (start_iso, end_iso),
        )
        return [
            {
                "history_id": r["history_id"],
                "lead_id": r["lead_id"],
                "old_status": r["old_status"],
                "new_status": r["new_status"],
                "timestamp": r["timestamp"],
            }
            for r in cur.fetchall()
        ]
