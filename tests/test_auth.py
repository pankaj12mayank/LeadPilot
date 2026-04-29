from __future__ import annotations

import uuid

import config
from backend.app.middleware.jwt import create_access_token


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


def test_role_access_buyer_can_export_but_not_leads(client):
    email = f"buyer_{uuid.uuid4().hex[:10]}@example.com"
    password = "pytest-password-9"
    reg = client.post(_api("/auth/register"), json={"email": email, "password": password, "role": "buyer"})
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    me = client.get(_api("/auth/me"), headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    assert me.json()["role"] == "buyer"

    denied = client.get(_api("/leads"), headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 403, denied.text

    allowed = client.get(_api("/exports/leads.csv"), headers={"Authorization": f"Bearer {token}"})
    assert allowed.status_code == 200, allowed.text


def test_buyer_marketplace_pack_purchase_and_download(client):
    buyer_email = f"buyer_market_{uuid.uuid4().hex[:8]}@example.com"
    password = "pytest-password-9"
    reg = client.post(_api("/auth/register"), json={"email": buyer_email, "password": password, "role": "buyer"})
    assert reg.status_code == 200, reg.text
    buyer_token = reg.json()["access_token"]

    admin_hdr = {"Authorization": f"Bearer {create_access_token('admin-test', {'admin': True})}"}
    create_pack = client.post(
        _api("/admin/lead-packs"),
        headers=admin_hdr,
        json={
            "name": "Starter Pack",
            "description": "Sample pack",
            "lead_ids": [],
            "price_usd": 49.0,
            "is_active": True,
        },
    )
    assert create_pack.status_code == 200, create_pack.text
    pack_id = int(create_pack.json()["id"])

    listed = client.get(_api("/exports/packs"), headers={"Authorization": f"Bearer {buyer_token}"})
    assert listed.status_code == 200, listed.text
    assert any(int(x["id"]) == pack_id for x in listed.json().get("items") or [])

    buy = client.post(_api(f"/exports/packs/{pack_id}/purchase"), headers={"Authorization": f"Bearer {buyer_token}"})
    assert buy.status_code == 200, buy.text
    assert buy.json().get("ok") is True

    dl = client.get(_api(f"/exports/packs/{pack_id}/download"), headers={"Authorization": f"Bearer {buyer_token}"})
    assert dl.status_code == 200, dl.text
