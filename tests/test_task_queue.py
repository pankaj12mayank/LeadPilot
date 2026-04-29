from __future__ import annotations

import uuid

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


def test_task_queue_priority_order(client):
    _drain_queue()
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    a = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={"task_type": "enrichment", "priority": "low", "requires_login": False, "payload": {"batch": "l1"}},
    )
    assert a.status_code == 200, a.text
    b = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={"task_type": "linkedin", "priority": "high", "requires_login": True, "payload": {"company_id": 99}},
    )
    assert b.status_code == 200, b.text
    c = client.post(
        _api("/tools/task-queue/enqueue"),
        headers=hdr,
        json={"task_type": "scoring", "priority": "medium", "requires_login": False, "payload": {"batch": "m1"}},
    )
    assert c.status_code == 200, c.text

    d1 = client.post(_api("/tools/task-queue/dequeue"), headers=hdr)
    d2 = client.post(_api("/tools/task-queue/dequeue"), headers=hdr)
    d3 = client.post(_api("/tools/task-queue/dequeue"), headers=hdr)
    assert d1.status_code == 200 and d2.status_code == 200 and d3.status_code == 200

    t1 = d1.json()["task"]
    t2 = d2.json()["task"]
    t3 = d3.json()["task"]
    assert t1["priority"] == "high"
    assert t2["priority"] == "medium"
    assert t3["priority"] == "low"
