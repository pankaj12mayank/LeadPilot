"""Detect lead source platform from the active page URL (no navigation)."""

from __future__ import annotations

from urllib.parse import urlparse


def detect_platform_from_url(url: str) -> str:
    """
    Return a canonical platform slug: linkedin, apollo, crunchbase, clutch, or generic.
    Matching is host/path based only (safe, no DOM access).
    """
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return "generic"
    host = (parsed.netloc or "").lower()

    if "linkedin.com" in host:
        return "linkedin"
    if "apollo.io" in host:
        return "apollo"
    if "crunchbase.com" in host:
        return "crunchbase"
    if "clutch.co" in host:
        return "clutch"
    return "generic"
