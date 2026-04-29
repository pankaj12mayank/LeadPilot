from __future__ import annotations

import json
import os
import socket
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import config
from backend.leadpilot.linkedin_session_cache import session_info_dict
from backend.services import company_enrichment_service, company_weekly_engine, lead_orm_service, runtime_settings, task_queue_service
from database.orm.bootstrap import get_session_factory
from database.orm.models import CompanyEnrichment
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _worker_logs_path() -> Path:
    config.ensure_data_dirs()
    root = Path(config.SESSIONS_DIR) / "job_logs"
    root.mkdir(parents=True, exist_ok=True)
    return root / "worker_runs.jsonl"


def _safe_int(v: Any) -> int:
    try:
        return int(v or 0)
    except Exception:
        return 0


def _records_processed_from_result(result: dict[str, Any]) -> int:
    if not isinstance(result, dict):
        return 0
    total = 0
    for key in ("saved_total", "stats", "score_refresh", "signal_refresh", "enrichment", "conversion"):
        row = result.get(key)
        if isinstance(row, dict):
            total += _safe_int(row.get("created"))
            total += _safe_int(row.get("updated"))
            total += _safe_int(row.get("selected"))
            total += _safe_int(row.get("ok"))
            total += _safe_int(row.get("processed"))
    total += _safe_int(result.get("records_processed"))
    return max(0, total)


def _errors_from_result(result: dict[str, Any], *, fallback_error: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(result, dict):
        for e in result.get("errors") or []:
            if str(e).strip():
                out.append(str(e))
        if result.get("error"):
            out.append(str(result.get("error")))
        if result.get("paused"):
            out.append("paused_for_manual_login")
    if fallback_error:
        out.append(fallback_error)
    # de-dup preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _append_worker_log(*, task: dict[str, Any], status: str, result: dict[str, Any], worker_id: str = "worker-1") -> dict[str, Any]:
    instance_id = _instance_id()
    task_type = str(task.get("task_type") or "unknown").strip().lower()
    records_processed = _records_processed_from_result(result)
    errors = _errors_from_result(result)
    row = {
        "run_date": datetime.now().isoformat(timespec="seconds"),
        "worker_id": worker_id,
        "instance_id": instance_id,
        "task_type": task_type,
        "status": status,
        "records_processed": records_processed,
        "errors": errors,
        "task": task,
        "result": result,
    }
    p = _worker_logs_path()
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _execute_task(db: Session, task: dict[str, Any]) -> dict[str, Any]:
    t = str(task.get("task_type") or "").strip().lower()
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    if t == "ingestion":
        return company_weekly_engine.run_daily_auto_job(
            db,
            keyword=str(payload.get("keyword") or "software"),
            location=str(payload.get("location") or ""),
            batch_size=int(payload.get("batch_size") or 10),
            delay_seconds=float(payload.get("delay_seconds") or 1.0),
        )
    if t == "enrichment":
        if str(payload.get("mode") or "").strip().lower() == "weekly_cleanup":
            out = company_weekly_engine.run_weekly_engine(db, day="sun")
            db.commit()
            return {"task_type": "enrichment", "cleanup": out.get("result") if isinstance(out, dict) else out}
        company_id = int(payload.get("company_id") or 0)
        ids = [company_id] if company_id > 0 else []
        stats = company_enrichment_service.enrich_companies_batch(
            db,
            company_ids=ids,
            limit=max(1, int(payload.get("limit") or (1 if ids else 20))),
            timeout_seconds=float(payload.get("timeout_seconds") or 10.0),
            delay_seconds=float(payload.get("delay_seconds") or 0.4),
        )
        db.commit()
        return {"task_type": "enrichment", "stats": stats}
    if t == "ai":
        company_id = int(payload.get("company_id") or 0)
        ids = [company_id] if company_id > 0 else []
        stats = company_enrichment_service.run_ai_qualification_batch(
            db,
            company_ids=ids,
            limit=max(1, int(payload.get("limit") or (1 if ids else 50))),
            live_ai=bool(payload.get("live_ai", False)),
        )
        db.commit()
        return {"task_type": "ai", "ai_refresh": stats}
    if t == "scoring":
        lead_stats = lead_orm_service.rescore_all_leads(db, limit=max(1, int(payload.get("lead_limit") or 5000)))
        company_stats = company_enrichment_service.rescore_all_companies(
            db, limit=max(1, int(payload.get("company_limit") or 5000))
        )
        db.commit()
        return {
            "task_type": "scoring",
            "score_refresh": {
                "processed": int(lead_stats.get("processed") or 0) + int(company_stats.get("processed") or 0),
                "leads_processed": int(lead_stats.get("processed") or 0),
                "companies_processed": int(company_stats.get("processed") or 0),
            },
        }
    if t == "signals":
        # signal refresh piggybacks on enrichment recalculation
        stats = company_enrichment_service.enrich_companies_batch(
            db,
            limit=max(1, int(payload.get("limit") or 20)),
            timeout_seconds=float(payload.get("timeout_seconds") or 10.0),
            delay_seconds=float(payload.get("delay_seconds") or 0.4),
        )
        db.commit()
        return {"task_type": "signals", "signal_refresh": stats}
    if t == "linkedin":
        return company_weekly_engine.run_weekly_engine(
            db,
            day="sat",
            saturday_min_score=float(payload.get("min_score") or 70.0),
            saturday_limit=int(payload.get("limit") or 30),
            saturday_manual_profiles=payload.get("manual_profiles") if isinstance(payload.get("manual_profiles"), list) else [],
            saturday_require_fresh_session=False,
        )
    raise ValueError(f"Unsupported task_type: {t}")


def _priority_for(task_type: str) -> str:
    cfg = runtime_settings.get_admin_config()
    mp = cfg.get("task_priority") or {}
    key = str(task_type or "").strip().lower()
    p = str(mp.get(key) or "").strip().lower()
    if not p and key == "ai":
        qp = cfg.get("queue_priority") or {}
        p = str(qp.get("ai") or "medium").strip().lower()
    if not p:
        p = "medium"
    return p if p in {"high", "medium", "low"} else "medium"


def _enqueue_chain(task_type: str, *, requires_login: bool = False, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return task_queue_service.enqueue(
        {
            "task_type": task_type,
            "priority": _priority_for(task_type),
            "requires_login": requires_login,
            "payload": payload or {"batch": "default"},
        }
    )


def _chain_next_tasks(db: Session, *, task: dict[str, Any], ok: bool) -> list[dict[str, Any]]:
    if not ok:
        return []
    t = str(task.get("task_type") or "").strip().lower()
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    chained: list[dict[str, Any]] = []
    if t == "ingestion":
        chained.append(_enqueue_chain("enrichment", payload={"batch": payload.get("batch") or "from_ingestion"}))
    elif t == "enrichment":
        chained.append(_enqueue_chain("ai", payload={"batch": payload.get("batch") or "from_enrichment"}))
    elif t == "ai":
        chained.append(_enqueue_chain("scoring", payload={"batch": payload.get("batch") or "from_signals"}))
    elif t == "signals":
        chained.append(_enqueue_chain("scoring", payload={"batch": payload.get("batch") or "from_signals"}))
    elif t == "scoring":
        min_score = runtime_settings.get_min_company_score()
        high = int(
            db.scalar(select(func.count(CompanyEnrichment.id)).where(func.coalesce(CompanyEnrichment.score, 0.0) >= float(min_score)))
            or 0
        )
        if high > 0:
            chained.append(
                _enqueue_chain(
                    "linkedin",
                    requires_login=True,
                    payload={"min_score": float(min_score), "limit": 30, "batch": "from_scoring"},
                )
            )
    return chained


def _execute_next_task_once(db: Session, *, worker_id: str = "worker-1") -> dict[str, Any]:
    """
    STEP W1 single-worker loop:
    dequeue -> check requires_login -> execute -> log result
    """
    # If normal queue is empty, try promoting waiting login tasks when session is valid.
    task = task_queue_service.dequeue(db=db)
    if not task and task_queue_service.waiting_size(db=db) > 0:
        sess = session_info_dict()
        if bool(sess.get("within_policy")):
            for w in task_queue_service.pop_waiting_ready(max_items=10, db=db):
                task_queue_service.enqueue(w, db=db)
            task = task_queue_service.dequeue(db=db)
    if not task:
        return {"status": "idle", "message": "No task in queue", "worker_id": worker_id, "instance_id": _instance_id()}

    if bool(task.get("requires_login")):
        sess = session_info_dict()
        if not bool(sess.get("within_policy")):
            # move blocked task into waiting queue
            waiting_task = task_queue_service.enqueue_waiting(task, reason="session_expired", db=db)
            out = {
                "status": "paused",
                "message": "Login-required task paused until session is valid",
                "session": sess,
                "notify_user": "LinkedIn session expired. Please login manually, then run worker again.",
                "waiting_queue_size": task_queue_service.waiting_size(db=db),
            }
            log = _append_worker_log(task=waiting_task, status="paused", result=out, worker_id=worker_id)
            return {
                "status": "paused",
                "task": waiting_task,
                "result": out,
                "log": log,
                "worker_id": worker_id,
                "instance_id": _instance_id(),
            }

    try:
        result = _execute_task(db, task)
        chained = _chain_next_tasks(db, task=task, ok=True)
        log = _append_worker_log(task=task, status="success", result=result, worker_id=worker_id)
        return {
            "status": "success",
            "task": task,
            "result": result,
            "chained_tasks": chained,
            "log": log,
            "worker_id": worker_id,
            "instance_id": _instance_id(),
        }
    except Exception as e:  # noqa: BLE001
        cfg = runtime_settings.get_admin_config()
        retry_cfg = cfg.get("retry_policy") or {}
        max_retries = max(1, min(10, int(retry_cfg.get("retry_count") or 3)))
        payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
        prev_attempt = max(0, int(payload.get("_retry_attempt") or 0))
        next_attempt = prev_attempt + 1
        err = {"ok": False, "error": str(e), "retry_attempt": next_attempt, "max_retries": max_retries}
        if next_attempt <= max_retries:
            retry_payload = dict(payload)
            retry_payload["_retry_attempt"] = next_attempt
            retry_payload["_last_error"] = str(e)
            retry_task = {
                "task_type": task.get("task_type"),
                "priority": task.get("priority"),
                "requires_login": task.get("requires_login"),
                "payload": retry_payload,
            }
            queued_retry = task_queue_service.enqueue(retry_task, db=db)
            err["retry_queued"] = True
            err["remaining_retries"] = max(0, max_retries - next_attempt)
            err["queued_task"] = queued_retry
            log = _append_worker_log(task=task, status="retrying", result=err, worker_id=worker_id)
            return {
                "status": "retrying",
                "task": task,
                "result": err,
                "log": log,
                "worker_id": worker_id,
                "instance_id": _instance_id(),
            }
        failed_payload = dict(payload)
        failed_payload["_retry_attempt"] = next_attempt
        failed_payload["_last_error"] = str(e)
        failed_task = {
            "task_type": task.get("task_type"),
            "priority": task.get("priority"),
            "requires_login": task.get("requires_login"),
            "payload": failed_payload,
        }
        moved = task_queue_service.enqueue_failed(failed_task, reason="max_retries_exceeded", db=db)
        err["retry_queued"] = False
        err["moved_to_failed_queue"] = True
        err["failed_task"] = moved
        log = _append_worker_log(task=failed_task, status="failure", result=err, worker_id=worker_id)
        return {
            "status": "failure",
            "task": failed_task,
            "result": err,
            "log": log,
            "worker_id": worker_id,
            "instance_id": _instance_id(),
        }


def execute_next_task(db: Session) -> dict[str, Any]:
    return _execute_next_task_once(db, worker_id="worker-1")


def _instance_id() -> str:
    """
    Machine/process identifier for distributed workers.
    Set LEADPILOT_WORKER_INSTANCE_ID to override.
    """
    env = str(os.environ.get("LEADPILOT_WORKER_INSTANCE_ID") or "").strip()
    if env:
        return env
    host = socket.gethostname().strip() or "unknown-host"
    pid = os.getpid()
    return f"{host}:{pid}"


def run_parallel_workers(*, worker_count: int = 3, max_tasks: int = 20) -> dict[str, Any]:
    """
    STEP W2 multi-worker execution:
    Run multiple workers in parallel and dynamically pull tasks from queue.
    """
    cfg = runtime_settings.get_admin_config()
    configured_workers = int(((cfg.get("worker_config") or {}).get("worker_count") or 3))
    requested_workers = int(worker_count or 0)
    wc = configured_workers if requested_workers <= 0 else requested_workers
    wc = max(1, min(wc, 12))
    mt = max(1, min(int(max_tasks or 20), 500))

    SessionLocal = get_session_factory()

    def _worker_loop(idx: int) -> list[dict[str, Any]]:
        worker_id = f"worker-{idx}"
        db = SessionLocal()
        out: list[dict[str, Any]] = []
        try:
            while len(out) < mt:
                step = _execute_next_task_once(db, worker_id=worker_id)
                out.append(step)
                if step.get("status") == "idle":
                    break
        finally:
            db.close()
        return out

    all_runs: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=wc) as ex:
        futures = [ex.submit(_worker_loop, i + 1) for i in range(wc)]
        for fut in futures:
            all_runs.extend(fut.result())

    processed = sum(1 for r in all_runs if r.get("status") in {"success", "failure", "paused", "retrying"})
    return {
        "instance_id": _instance_id(),
        "workers": wc,
        "max_tasks_per_worker": mt,
        "processed": processed,
        "queue_size": task_queue_service.size(),
        "waiting_queue_size": task_queue_service.waiting_size(),
        "failed_queue_size": task_queue_service.failed_size(),
        "runs": all_runs,
    }


def run_worker_instance_loop(
    *,
    worker_count: int = 1,
    max_tasks_per_worker: int = 10,
    poll_seconds: float = 2.0,
    max_cycles: int = 0,
) -> dict[str, Any]:
    """
    Distributed worker loop for standalone machines.
    Each cycle pulls from shared DB queue.
    - max_cycles=0 means run forever.
    """
    cycles = 0
    total_processed = 0
    while True:
        cycles += 1
        out = run_parallel_workers(worker_count=worker_count, max_tasks=max_tasks_per_worker)
        total_processed += int(out.get("processed") or 0)
        if max_cycles > 0 and cycles >= max_cycles:
            return {
                "instance_id": _instance_id(),
                "cycles": cycles,
                "total_processed": total_processed,
                "queue_size": task_queue_service.size(),
                "waiting_queue_size": task_queue_service.waiting_size(),
                "failed_queue_size": task_queue_service.failed_size(),
                "mode": "loop_stopped",
            }
        if int(out.get("processed") or 0) == 0:
            time.sleep(max(0.2, float(poll_seconds or 2.0)))
