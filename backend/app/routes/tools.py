"""Operational tools exposed over the API (no command-line workflows)."""

from __future__ import annotations

from typing import Optional

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.deps import get_current_user
from backend.lead_cleaning.engine import run_cleaning_pipeline
from backend.lead_cleaning.summary import CleaningSummary
from database.migrate_from_csv import migrate as migrate_csv_to_sqlite
from backend.services import bulk_message_service

router = APIRouter(prefix="/tools", tags=["tools"])


class MigrateCsvBody(BaseModel):
    csv_path: Optional[str] = None
    db_path: Optional[str] = None


@router.post("/migrate-csv-to-sqlite")
def migrate_csv_to_sqlite_endpoint(
    body: MigrateCsvBody = MigrateCsvBody(),
    _user: dict = Depends(get_current_user),
) -> dict:
    """Copy normalized leads from CSV storage into SQLite (uses config paths when omitted)."""
    n = migrate_csv_to_sqlite(csv_path=body.csv_path, db_path=body.db_path)
    return {"migrated": n, "message": f"Imported {n} lead(s) into SQLite."}


@router.post("/generate-pending-messages")
def generate_pending_messages(_user: dict = Depends(get_current_user)) -> dict:
    """Generate subject + message for every lead that has an empty message field."""
    n = bulk_message_service.generate_for_all_pending()
    return {"processed": n, "message": f"Updated {n} lead(s)."}


class CleanLeadsCsvBody(BaseModel):
    """Path to a CSV file to clean (writes ``raw_leads.csv``, ``cleaned_leads.csv``, ``enriched_leads.csv`` to exports)."""

    input_csv_path: str


@router.post("/clean-leads-csv")
def clean_leads_csv_endpoint(
    body: CleanLeadsCsvBody,
    _user: dict = Depends(get_current_user),
) -> dict:
    if not os.path.isfile(body.input_csv_path):
        raise HTTPException(status_code=400, detail=f"File not found: {body.input_csv_path}")
    try:
        summary: CleaningSummary = run_cleaning_pipeline(body.input_csv_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"summary": summary.to_dict()}
