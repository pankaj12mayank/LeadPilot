from __future__ import annotations

import uuid

import config


def _api(subpath: str) -> str:
    """Paths under ``config.API_ROOT_PATH`` (default ``/api``)."""
    p = subpath if subpath.startswith("/") else f"/{subpath}"
    root = (config.API_ROOT_PATH or "").rstrip("/")
    return f"{root}{p}" if root else p


def test_register_and_login(client):
    email = f"pytest_{uuid.uuid4().hex[:12]}@example.com"
    password = "pytest-password-9"

    reg = client.post(_api("/auth/register"), json={"email": email, "password": password})
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    assert token

    me = client.get(_api("/auth/me"), headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email.lower()

    login = client.post(_api("/auth/login"), json={"email": email, "password": password})
    assert login.status_code == 200
    assert login.json()["access_token"]
