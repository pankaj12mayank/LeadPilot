from __future__ import annotations

import config
from backend.app.middleware.jwt import create_access_token


def _api(subpath: str) -> str:
    p = subpath if subpath.startswith("/") else f"/{subpath}"
    root = (config.API_ROOT_PATH or "").rstrip("/")
    return f"{root}{p}" if root else p


def _admin_headers() -> dict[str, str]:
    tok = create_access_token("admin-test", {"admin": True})
    return {"Authorization": f"Bearer {tok}"}


def test_admin_landing_get_and_patch_config(client):
    hdr = _admin_headers()
    got = client.get(_api("/admin/landing/config"), headers=hdr)
    assert got.status_code == 200, got.text
    cfg = got.json()["config"]
    assert "sections" in cfg
    assert "seo" in cfg
    assert "theme" in cfg

    cfg["seo"]["title"] = "LeadPilot Custom SEO Title"
    cfg["geo"]["location_label"] = "Mumbai"
    cfg["sections"][0]["heading"] = "Dynamic Hero Heading"
    cfg["sections"][0]["enabled"] = True
    cfg["sections"][0]["order"] = 2
    cfg["sections"][1]["order"] = 1

    patched = client.patch(_api("/admin/landing/config"), headers=hdr, json={"config": cfg})
    assert patched.status_code == 200, patched.text
    out = patched.json()["config"]
    assert out["seo"]["title"] == "LeadPilot Custom SEO Title"
    assert out["geo"]["location_label"] == "Mumbai"
    assert out["sections"][0]["heading"] == "Dynamic Hero Heading"

    pub = client.get(_api("/public/landing-config"))
    assert pub.status_code == 200, pub.text
    pub_cfg = pub.json()["config"]
    assert pub_cfg["seo"]["title"] == "LeadPilot Custom SEO Title"


def test_admin_landing_generate_content_and_public_tracking(client):
    hdr = _admin_headers()
    gen = client.post(
        _api("/admin/landing/generate-content"),
        headers=hdr,
        json={"location": "Delhi", "keyword_focus": "B2B AI leads"},
    )
    assert gen.status_code == 200, gen.text
    body = gen.json()
    assert body["ok"] is True
    generated = body["generated"]
    assert "hero_heading" in generated
    assert "hero_subheading" in generated
    assert "cta_text" in generated

    track = client.post(
        _api("/public/landing-track"),
        json={"event": "cta_click", "section": "hero", "target": "/login"},
    )
    assert track.status_code == 200, track.text
    assert track.json()["ok"] is True
