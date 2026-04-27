from __future__ import annotations

from typing import Dict, Type

from backend.scraper.base import BaseScraper
from backend.scraper.platforms.linkedin import LinkedInScraper

# ---------------------------------------------------------------------------
# LinkedIn-only execution path (see root ``main.py`` / ``backend.pipeline``).
# Add platform modules under ``platforms/`` and register here to enable more sources.
# ---------------------------------------------------------------------------

PLATFORMS: Dict[str, Type[BaseScraper]] = {
    "linkedin": LinkedInScraper,
}


def get_scraper_class(platform_slug: str) -> Type[BaseScraper] | None:
    key = platform_slug.strip().lower().replace(" ", "_")
    return PLATFORMS.get(key)


def list_platform_slugs() -> list[str]:
    return sorted(PLATFORMS.keys())
