from __future__ import annotations

from backend.connectors.platforms import PLATFORM_ALIASES, PLATFORM_CANONICAL


def normalize_platform(raw: str | None) -> str:
    if not raw:
        return "other"
    key = raw.strip().lower().replace("-", " ")
    slug = PLATFORM_ALIASES.get(key, key.replace(" ", "_"))
    if slug in PLATFORM_CANONICAL:
        return slug
    return "other"


def is_known_platform(canonical: str) -> bool:
    return canonical in PLATFORM_CANONICAL
