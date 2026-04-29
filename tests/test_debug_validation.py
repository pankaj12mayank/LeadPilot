from __future__ import annotations

import uuid

import config


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


def test_debug_mode_toggle_and_validation_endpoint(client):
    token = _token(client)
    hdr = {"Authorization": f"Bearer {token}"}

    g = client.get(_api("/settings/debug-mode"), headers=hdr)
    assert g.status_code == 200, g.text
    assert "enabled" in g.json()

    p = client.patch(_api("/settings/debug-mode"), headers=hdr, json={"enabled": True})
    assert p.status_code == 200, p.text
    assert p.json()["enabled"] is True

    v = client.get("/validation", headers=hdr)
    assert v.status_code == 200, v.text
    body = v.json()
    assert "pipeline_checks" in body
    assert "db_checks" in body
    assert "source_checks" in body
    assert body["debug_mode"] is True
