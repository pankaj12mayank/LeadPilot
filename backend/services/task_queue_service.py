from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from database.orm.bootstrap import get_session_factory
from database.orm.models import TaskQueueItem
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _normalize_priority(priority: str) -> str:
    p = str(priority or "medium").strip().lower()
    return p if p in PRIORITY_ORDER else "medium"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _session(db: Session | None = None) -> tuple[Session, bool]:
    if db is not None:
        return db, False
    SessionLocal = get_session_factory()
    return SessionLocal(), True


def _to_task(row: TaskQueueItem) -> dict[str, Any]:
    try:
        payload = json.loads(row.payload_json or "{}")
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    out = {
        "task_type": str(row.task_type or "ingestion").strip().lower(),
        "priority": _normalize_priority(row.priority),
        "requires_login": bool(row.requires_login),
        "payload": payload,
    }
    if row.waiting_reason:
        out["waiting_reason"] = row.waiting_reason
    return out


def enqueue(task: dict[str, Any], *, db: Session | None = None) -> dict[str, Any]:
    """
    Push a task into the shared DB queue.
    Expected shape: task_type, priority, requires_login, payload.
    """
    item = {
        "task_type": str(task.get("task_type") or "ingestion").strip().lower(),
        "priority": _normalize_priority(str(task.get("priority") or "medium")),
        "requires_login": bool(task.get("requires_login", False)),
        "payload": task.get("payload") if isinstance(task.get("payload"), dict) else {"batch": "default"},
    }
    sx, close = _session(db)
    try:
        now = _now()
        row = TaskQueueItem(
            task_type=item["task_type"],
            priority=item["priority"],
            requires_login=1 if item["requires_login"] else 0,
            payload_json=json.dumps(item["payload"], ensure_ascii=False),
            queue_state="queued",
            waiting_reason="",
            created_at=now,
            updated_at=now,
        )
        sx.add(row)
        sx.commit()
    finally:
        if close:
            sx.close()
    return item


def dequeue(*, db: Session | None = None) -> dict[str, Any] | None:
    """
    Pop next queued task (high priority first) from shared DB queue.
    Best-effort atomic claim+delete loop for multi-worker safety.
    """
    sx, close = _session(db)
    try:
        for _ in range(8):
            rows = list(
                sx.scalars(
                    select(TaskQueueItem)
                    .where(TaskQueueItem.queue_state == "queued")
                    .order_by(TaskQueueItem.id.asc())
                    .limit(200)
                )
            )
            if not rows:
                return None
            rows.sort(key=lambda r: (_PRIORITY_RANK.get(_normalize_priority(r.priority), 1), int(r.id)))
            chosen = rows[0]
            res = sx.execute(
                delete(TaskQueueItem).where(
                    TaskQueueItem.id == int(chosen.id),
                    TaskQueueItem.queue_state == "queued",
                )
            )
            if int(res.rowcount or 0) == 1:
                sx.commit()
                return _to_task(chosen)
            sx.rollback()
        return None
    finally:
        if close:
            sx.close()


def size(*, db: Session | None = None) -> int:
    sx, close = _session(db)
    try:
        return int(sx.scalar(select(func.count(TaskQueueItem.id)).where(TaskQueueItem.queue_state == "queued")) or 0)
    finally:
        if close:
            sx.close()


def enqueue_waiting(task: dict[str, Any], *, reason: str = "waiting_for_login", db: Session | None = None) -> dict[str, Any]:
    item = {
        "task_type": str(task.get("task_type") or "ingestion").strip().lower(),
        "priority": _normalize_priority(str(task.get("priority") or "medium")),
        "requires_login": bool(task.get("requires_login", False)),
        "payload": task.get("payload") if isinstance(task.get("payload"), dict) else {"batch": "default"},
        "waiting_reason": str(reason or "waiting_for_login"),
    }
    sx, close = _session(db)
    try:
        now = _now()
        row = TaskQueueItem(
            task_type=item["task_type"],
            priority=item["priority"],
            requires_login=1 if item["requires_login"] else 0,
            payload_json=json.dumps(item["payload"], ensure_ascii=False),
            queue_state="waiting",
            waiting_reason=item["waiting_reason"],
            created_at=now,
            updated_at=now,
        )
        sx.add(row)
        sx.commit()
    finally:
        if close:
            sx.close()
    return item


def enqueue_failed(task: dict[str, Any], *, reason: str = "task_failed", db: Session | None = None) -> dict[str, Any]:
    item = {
        "task_type": str(task.get("task_type") or "ingestion").strip().lower(),
        "priority": _normalize_priority(str(task.get("priority") or "medium")),
        "requires_login": bool(task.get("requires_login", False)),
        "payload": task.get("payload") if isinstance(task.get("payload"), dict) else {"batch": "default"},
        "waiting_reason": str(reason or "task_failed"),
    }
    sx, close = _session(db)
    try:
        now = _now()
        row = TaskQueueItem(
            task_type=item["task_type"],
            priority=item["priority"],
            requires_login=1 if item["requires_login"] else 0,
            payload_json=json.dumps(item["payload"], ensure_ascii=False),
            queue_state="failed",
            waiting_reason=item["waiting_reason"],
            created_at=now,
            updated_at=now,
        )
        sx.add(row)
        sx.commit()
    finally:
        if close:
            sx.close()
    return item


def pop_waiting_ready(*, max_items: int = 1, db: Session | None = None) -> list[dict[str, Any]]:
    n = max(0, int(max_items or 0))
    if n <= 0:
        return []
    sx, close = _session(db)
    out: list[dict[str, Any]] = []
    try:
        rows = list(
            sx.scalars(
                select(TaskQueueItem)
                .where(TaskQueueItem.queue_state == "waiting")
                .order_by(TaskQueueItem.id.asc())
                .limit(n)
            )
        )
        for row in rows:
            out.append(_to_task(row))
            sx.execute(delete(TaskQueueItem).where(TaskQueueItem.id == int(row.id), TaskQueueItem.queue_state == "waiting"))
        if rows:
            sx.commit()
        return out
    finally:
        if close:
            sx.close()


def waiting_size(*, db: Session | None = None) -> int:
    sx, close = _session(db)
    try:
        return int(sx.scalar(select(func.count(TaskQueueItem.id)).where(TaskQueueItem.queue_state == "waiting")) or 0)
    finally:
        if close:
            sx.close()


def failed_size(*, db: Session | None = None) -> int:
    sx, close = _session(db)
    try:
        return int(sx.scalar(select(func.count(TaskQueueItem.id)).where(TaskQueueItem.queue_state == "failed")) or 0)
    finally:
        if close:
            sx.close()


def clear_all_for_tests(*, db: Session | None = None) -> None:
    sx, close = _session(db)
    try:
        sx.execute(delete(TaskQueueItem))
        sx.commit()
    finally:
        if close:
            sx.close()
