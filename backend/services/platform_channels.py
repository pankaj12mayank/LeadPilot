"""Active platform slugs for scraper, filters, and session verification."""

from __future__ import annotations

from typing import List

from backend.connectors.platforms import PLATFORM_CANONICAL

from backend.services import platform_registry_service


def active_channel_slugs() -> List[str]:
    out: List[str] = []
    for s in sorted(PLATFORM_CANONICAL | {"other"}):
        if platform_registry_service.get_builtin_active(s):
            out.append(s)
    for row in platform_registry_service.list_custom():
        if row.get("active"):
            out.append(str(row["slug"]))
    return out
