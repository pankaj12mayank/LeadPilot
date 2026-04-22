"""Outbound email audit trail (CRM meta DB)."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from database.meta_db import init_meta_schema, meta_connection
from backend.settings.lead_schema import utc_now_iso


def record(
    lead_id: str,
    recipient_email: str,
    subject: str,
    body: str,
    status: str,
) -> str:
    init_meta_schema()
    eid = str(uuid.uuid4())
    with meta_connection() as cx:
        cx.execute(
            """
            INSERT INTO email_history (email_id, lead_id, recipient_email, subject, body, status, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (eid, lead_id, recipient_email, subject, body, status, utc_now_iso()),
        )
    return eid


def list_for_lead(lead_id: str) -> List[Dict[str, Any]]:
    init_meta_schema()
    with meta_connection() as cx:
        cur = cx.execute(
            """
            SELECT email_id, lead_id, recipient_email, subject, body, status, sent_at
            FROM email_history WHERE lead_id = ? ORDER BY sent_at ASC
            """,
            (lead_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def list_between(start_iso: str, end_iso: str) -> List[Dict[str, Any]]:
    """Email rows with ``sent_at`` in ``[start_iso, end_iso]`` (inclusive)."""
    init_meta_schema()
    with meta_connection() as cx:
        cur = cx.execute(
            """
            SELECT email_id, lead_id, recipient_email, subject, body, status, sent_at
            FROM email_history
            WHERE sent_at >= ? AND sent_at <= ?
            ORDER BY sent_at ASC
            """,
            (start_iso, end_iso),
        )
        return [dict(r) for r in cur.fetchall()]


def aggregate_between(start_iso: str, end_iso: str) -> Dict[str, Any]:
    """Counts for analytics (reply / send denominators)."""
    rows = list_between(start_iso, end_iso)
    sent = sum(1 for r in rows if str(r.get("status") or "").lower() == "sent")
    failed = sum(1 for r in rows if str(r.get("status") or "").lower().startswith("failed"))
    skipped = sum(1 for r in rows if "skipped" in str(r.get("status") or "").lower())
    replied = sum(
        1
        for r in rows
        if "reply" in str(r.get("status") or "").lower() or str(r.get("status") or "").lower() == "replied"
    )
    leads_emailed = len({str(r.get("lead_id") or "") for r in rows if r.get("lead_id")})
    leads_replied = len(
        {
            str(r.get("lead_id") or "")
            for r in rows
            if r.get("lead_id")
            and ("reply" in str(r.get("status") or "").lower() or str(r.get("status") or "").lower() == "replied")
        }
    )
    return {
        "total_rows": len(rows),
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "reply_rows": replied,
        "distinct_leads_emailed": leads_emailed,
        "distinct_leads_replied": leads_replied,
    }
