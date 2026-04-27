"""Selenium leadpilot REST helpers (auth required)."""

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


def test_selenium_leadpilot_status_requires_auth(client):
    r = client.get(_api("/scraper/selenium-leadpilot/status"))
    assert r.status_code == 401


def test_selenium_leadpilot_status_ok(client):
    token = _token(client)
    r = client.get(
        _api("/scraper/selenium-leadpilot/status"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "state" in data
    assert data.get("available") in (True, False)
