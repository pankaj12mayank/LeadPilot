from __future__ import annotations

import uuid
from unittest.mock import patch

import config
from backend.services import task_queue_service


def _api(subpath: str) -> str:
    p = subpath if subpath.startswith("/") else f"/{subpath}"
    root = (config.API_ROOT_PATH or "").rstrip("/")
    return f"{root}{p}" if root else p


def _token(client) -> str:
    email = f"pytest_{uuid.uuid4().hex[:12]}@example.com"
    password = "pytest-password-9"
    reg = client.post(_api("/auth/register"), json={"email": email, "password": password})
    assert reg.status_code == 200, reg.text
    return reg.json()["access_token"]


def _drain_queue() -> None:
    task_queue_service.clear_all_for_tests()


def test_worker_executes_task(client):
    _drain_queue()
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    q = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={"task_type": "enrichment", "priority": "medium", "requires_login": False, "payload": {"limit": 1}},
    )
    assert q.status_code == 200, q.text

    with patch(
        "backend.services.task_worker_service.company_enrichment_service.enrich_companies_batch",
        return_value={"selected": 0, "ok": 0, "failed": 0, "skipped": 0},
    ):
        r = client.post(_api("/tools/task-worker/run-once"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert body["task"]["task_type"] == "enrichment"
    log = body.get("log") or {}
    assert log.get("task_type") == "enrichment"
    assert log.get("status") == "success"
    assert "records_processed" in log
    assert isinstance(log.get("errors"), list)


def test_worker_pauses_login_required_task(client):
    _drain_queue()
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    q = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={"task_type": "linkedin", "priority": "high", "requires_login": True, "payload": {}},
    )
    assert q.status_code == 200, q.text

    with patch(
        "backend.services.task_worker_service.session_info_dict",
        return_value={"has_cache": True, "within_policy": False, "policy_days": 7},
    ):
        r = client.post(_api("/tools/task-worker/run-once"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "paused"
    assert body["task"]["task_type"] == "linkedin"
    assert body["result"]["waiting_queue_size"] >= 1
    assert "notify_user" in body["result"]
    log = body.get("log") or {}
    assert log.get("task_type") == "linkedin"
    assert log.get("status") == "paused"


def test_parallel_workers_execute_tasks_dynamically(client):
    _drain_queue()
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    for i in range(3):
        q = client.post(
            _api("/tools/task-queue/enqueue"),
            headers=hdr,
            json={"task_type": "enrichment", "priority": "medium", "requires_login": False, "payload": {"limit": 1, "n": i}},
        )
        assert q.status_code == 200, q.text

    with patch(
        "backend.services.task_worker_service.company_enrichment_service.enrich_companies_batch",
        return_value={"selected": 0, "ok": 0, "failed": 0, "skipped": 0},
    ):
        r = client.post(
            _api("/tools/task-worker/run-parallel"),
            headers=hdr,
            json={"worker_count": 3, "max_tasks_per_worker": 2},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workers"] == 3
    assert body["instance_id"]
    assert body["processed"] >= 3
    worker_ids = {x.get("worker_id") for x in body.get("runs", []) if x.get("worker_id")}
    assert len(worker_ids) >= 2


def test_worker_chains_next_task_after_success(client):
    _drain_queue()
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    q = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={"task_type": "ingestion", "priority": "low", "requires_login": False, "payload": {"batch": "seed"}},
    )
    assert q.status_code == 200, q.text

    with patch(
        "backend.services.task_worker_service.company_weekly_engine.run_daily_auto_job",
        return_value={"ok": True},
    ):
        r = client.post(_api("/tools/task-worker/run-once"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    chained = body.get("chained_tasks") or []
    assert any(x.get("task_type") == "enrichment" for x in chained)

    # The next task available should be enrichment from chain.
    d = client.post(_api("/tools/task-queue/dequeue"), headers=hdr)
    assert d.status_code == 200, d.text
    nxt = d.json().get("task") or {}
    assert nxt.get("task_type") == "enrichment"


def test_worker_chains_ai_after_enrichment(client):
    _drain_queue()
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    q = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={"task_type": "enrichment", "priority": "medium", "requires_login": False, "payload": {"limit": 1}},
    )
    assert q.status_code == 200, q.text

    with patch(
        "backend.services.task_worker_service.company_enrichment_service.enrich_companies_batch",
        return_value={"selected": 1, "ok": 1, "failed": 0, "skipped": 0},
    ):
        r = client.post(_api("/tools/task-worker/run-once"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    chained = body.get("chained_tasks") or []
    assert any(x.get("task_type") == "ai" for x in chained)


def test_worker_executes_ai_task(client):
    _drain_queue()
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    q = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={"task_type": "ai", "priority": "medium", "requires_login": False, "payload": {"limit": 2}},
    )
    assert q.status_code == 200, q.text

    with patch(
        "backend.services.task_worker_service.company_enrichment_service.run_ai_qualification_batch",
        return_value={"processed": 2, "cached": 1},
    ):
        r = client.post(_api("/tools/task-worker/run-once"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    ai_refresh = ((body.get("result") or {}).get("ai_refresh") or {})
    assert int(ai_refresh.get("processed") or 0) == 2


def test_worker_retries_failed_task(client):
    _drain_queue()
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    q = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={"task_type": "enrichment", "priority": "medium", "requires_login": False, "payload": {"limit": 1}},
    )
    assert q.status_code == 200, q.text

    with patch(
        "backend.services.task_worker_service.company_enrichment_service.enrich_companies_batch",
        side_effect=RuntimeError("enrichment boom"),
    ):
        r = client.post(_api("/tools/task-worker/run-once"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "retrying"
    assert body["result"]["retry_queued"] is True

    d = client.post(_api("/tools/task-queue/dequeue"), headers=hdr)
    assert d.status_code == 200, d.text
    nxt = d.json().get("task") or {}
    assert nxt.get("task_type") == "enrichment"
    assert int((nxt.get("payload") or {}).get("_retry_attempt") or 0) == 1


def test_worker_moves_task_to_failed_queue_after_retries_exhausted(client):
    _drain_queue()
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    q = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={
            "task_type": "enrichment",
            "priority": "medium",
            "requires_login": False,
            "payload": {"limit": 1, "_retry_attempt": 1},
        },
    )
    assert q.status_code == 200, q.text

    with patch(
        "backend.services.task_worker_service.runtime_settings.get_admin_config",
        return_value={"retry_policy": {"retry_count": 1}, "task_priority": {}},
    ), patch(
        "backend.services.task_worker_service.company_enrichment_service.enrich_companies_batch",
        side_effect=RuntimeError("still failing"),
    ):
        r = client.post(_api("/tools/task-worker/run-once"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "failure"
    assert body["result"]["moved_to_failed_queue"] is True

    st = client.get(_api("/tools/task-queue/status"), headers=hdr)
    assert st.status_code == 200, st.text
    assert int(st.json().get("failed_queue_size") or 0) >= 1


def test_worker_scoring_recomputes_leads_and_companies(client):
    _drain_queue()
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    q = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={"task_type": "scoring", "priority": "high", "requires_login": False, "payload": {"batch": "refresh"}},
    )
    assert q.status_code == 200, q.text

    with patch(
        "backend.services.task_worker_service.lead_orm_service.rescore_all_leads",
        return_value={"processed": 3},
    ), patch(
        "backend.services.task_worker_service.company_enrichment_service.rescore_all_companies",
        return_value={"processed": 2},
    ):
        r = client.post(_api("/tools/task-worker/run-once"), headers=hdr)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    refresh = (body.get("result") or {}).get("score_refresh") or {}
    assert int(refresh.get("leads_processed") or 0) == 3
    assert int(refresh.get("companies_processed") or 0) == 2
