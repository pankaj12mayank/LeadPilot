"""Canonical lead field definitions used by CSV, SQLite, and services."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

LEAD_COLUMNS: List[str] = [
    "lead_id",
    "name",
    "email",
    "phone",
    "company",
    "platform",
    "profile_url",
    "location",
    "notes",
    "subject",
    "message",
    "score",
    "tier",
    "status",
    "created_at",
    "updated_at",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_lead_id() -> str:
    return str(uuid.uuid4())


def empty_lead_dict() -> Dict[str, Any]:
    return {c: "" for c in LEAD_COLUMNS}


def normalize_lead_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Merge a partial or legacy row into the full schema with safe defaults."""
    base = empty_lead_dict()
    for key in LEAD_COLUMNS:
        if key in row and row[key] is not None and str(row[key]).lower() != "nan":
            val = row[key]
            if key in ("score",) and val != "":
                try:
                    base[key] = float(val)
                except (TypeError, ValueError):
                    base[key] = 0.0
            else:
                base[key] = val if val is not None else ""
    if not base.get("lead_id"):
        base["lead_id"] = new_lead_id()
    if not base.get("created_at"):
        base["created_at"] = utc_now_iso()
    if not base.get("updated_at"):
        base["updated_at"] = base["created_at"]
    return base


def row_for_write(row: Dict[str, Any]) -> Dict[str, Any]:
    out = normalize_lead_row(row)
    for k in LEAD_COLUMNS:
        if k == "score" and out[k] == "":
            out[k] = 0.0
        elif out[k] is None:
            out[k] = ""
    return {k: out[k] for k in LEAD_COLUMNS}
