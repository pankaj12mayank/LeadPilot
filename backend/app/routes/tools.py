"""Operational tools exposed over the API (no command-line workflows)."""

from __future__ import annotations

from typing import Any, Optional

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.deps import get_current_user, get_db
from backend.lead_cleaning.engine import run_cleaning_pipeline
from backend.lead_cleaning.summary import CleaningSummary
from database.migrate_from_csv import migrate as migrate_csv_to_sqlite
from sqlalchemy.orm import Session
from backend.services import bulk_message_service, task_queue_service, task_worker_service

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


class QueueTaskBody(BaseModel):
    task_type: str
    priority: str = "medium"
    requires_login: bool = False
    payload: dict[str, Any] = {}


class ParallelWorkerBody(BaseModel):
    worker_count: int = 3
    max_tasks_per_worker: int = 20


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


@router.post("/task-queue/enqueue")
def enqueue_task(
    body: QueueTaskBody,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    task = task_queue_service.enqueue(
        {
            "task_type": body.task_type,
            "priority": body.priority,
            "requires_login": body.requires_login,
            "payload": body.payload,
        }
    )
    return {
        "enqueued": task,
        "queue_size": task_queue_service.size(db=db),
        "waiting_queue_size": task_queue_service.waiting_size(db=db),
        "failed_queue_size": task_queue_service.failed_size(db=db),
    }


@router.post("/task-queue/dequeue")
def dequeue_task(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    task = task_queue_service.dequeue(db=db)
    return {
        "task": task,
        "queue_size": task_queue_service.size(db=db),
        "waiting_queue_size": task_queue_service.waiting_size(db=db),
        "failed_queue_size": task_queue_service.failed_size(db=db),
    }


@router.get("/task-queue/status")
def task_queue_status(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, int]:
    return {
        "queue_size": task_queue_service.size(db=db),
        "waiting_queue_size": task_queue_service.waiting_size(db=db),
        "failed_queue_size": task_queue_service.failed_size(db=db),
    }


@router.post("/task-worker/run-once")
def run_task_worker_once(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return task_worker_service.execute_next_task(db)


@router.post("/task-worker/run-parallel")
def run_task_worker_parallel(
    body: ParallelWorkerBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return task_worker_service.run_parallel_workers(
        worker_count=body.worker_count,
        max_tasks=body.max_tasks_per_worker,
    )
