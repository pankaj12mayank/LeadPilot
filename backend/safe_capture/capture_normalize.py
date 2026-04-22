"""Normalize connector output into the common LeadPilot safe-capture schema."""

from __future__ import annotations

from typing import Any


def normalize_parsed_lead(raw: dict[str, Any], source_platform: str) -> dict[str, Any]:
    """
    Build a dict with all canonical keys (placeholders filled before scoring).

    Status always starts as ``NEW`` for a freshly captured lead.
    """
    slug = (source_platform or "generic").strip().lower()

    def _s(key: str) -> str:
        return str(raw.get(key) or "").strip()

    profile_url = _s("profile_url")
    if not profile_url and isinstance(raw.get("url"), str):
        profile_url = str(raw["url"]).strip()

    return {
        "name": _s("name"),
        "title": _s("title"),
        "company": _s("company"),
        "industry": _s("industry"),
        "location": _s("location"),
        "website": _s("website"),
        "email": _s("email"),
        "source_platform": slug,
        "profile_url": profile_url,
        "score": 0,
        "tier": "COLD",
        "status": "NEW",
    }
