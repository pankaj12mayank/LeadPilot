"""Lead audit trail stored in API meta DB (does not affect CSV lead schema)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from database.meta_db import init_meta_schema, meta_connection
from backend.settings.lead_schema import utc_now_iso


def record_event(
    lead_id: Optional[str],
    action: str,
    detail: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> None:
    init_meta_schema()
    detail_str = json.dumps(detail) if detail is not None else None
    with meta_connection() as cx:
        cx.execute(
            """
            INSERT INTO lead_history (lead_id, action, detail, user_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lead_id, action, detail_str, user_id, utc_now_iso()),
        )


def list_for_lead(lead_id: str) -> List[Dict[str, Any]]:
    init_meta_schema()
    with meta_connection() as cx:
        cur = cx.execute(
            """
            SELECT id, lead_id, action, detail, user_id, created_at
            FROM lead_history WHERE lead_id = ? ORDER BY id ASC
            """,
            (lead_id,),
        )
        rows = []
        for r in cur.fetchall():
            rows.append(
                {
                    "id": r["id"],
                    "lead_id": r["lead_id"],
                    "action": r["action"],
                    "detail": json.loads(r["detail"]) if r["detail"] else None,
                    "user_id": r["user_id"],
                    "created_at": r["created_at"],
                }
            )
        return rows


def count_recent(days: int = 7) -> int:
    init_meta_schema()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat()
    with meta_connection() as cx:
        cur = cx.execute(
            "SELECT COUNT(*) FROM lead_history WHERE created_at >= ?", (cutoff,)
        )
        return int(cur.fetchone()[0])


def list_events_between(start_iso: str, end_iso: str) -> List[Dict[str, Any]]:
    """Return lead_history rows with ``created_at`` in ``[start_iso, end_iso]`` (inclusive)."""
    init_meta_schema()
    with meta_connection() as cx:
        cur = cx.execute(
            """
            SELECT id, lead_id, action, detail, user_id, created_at
            FROM lead_history
            WHERE created_at >= ? AND created_at <= ?
            ORDER BY created_at ASC
            """,
            (start_iso, end_iso),
        )
        rows: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            detail_raw = r["detail"]
            detail_obj: Any = None
            if detail_raw:
                try:
                    detail_obj = json.loads(detail_raw)
                except Exception:
                    detail_obj = {"_unparsed": str(detail_raw)}
            rows.append(
                {
                    "id": r["id"],
                    "lead_id": r["lead_id"],
                    "action": r["action"],
                    "detail": detail_obj,
                    "user_id": r["user_id"],
                    "created_at": r["created_at"],
                }
            )
        return rows


def count_events_by_action_between(start_iso: str, end_iso: str) -> Dict[str, int]:
    init_meta_schema()
    with meta_connection() as cx:
        cur = cx.execute(
            """
            SELECT action, COUNT(*) AS c
            FROM lead_history
            WHERE created_at >= ? AND created_at <= ?
            GROUP BY action
            """,
            (start_iso, end_iso),
        )
        return {str(r["action"]): int(r["c"]) for r in cur.fetchall()}
