from __future__ import annotations

from typing import Dict, Type

from backend.scraper.base import BaseScraper
from backend.scraper.platforms.linkedin import LinkedInScraper

# ---------------------------------------------------------------------------
# LinkedIn-only execution path (see ``main.py`` / ``backend.pipeline``).
# Other platform scrapers remain on disk for future use but are not registered
# and must not be imported here (keeps runtime free of multi-source routing).
# ---------------------------------------------------------------------------

PLATFORMS: Dict[str, Type[BaseScraper]] = {
    "linkedin": LinkedInScraper,
}


def get_scraper_class(platform_slug: str) -> Type[BaseScraper] | None:
    key = platform_slug.strip().lower().replace(" ", "_")
    return PLATFORMS.get(key)


def list_platform_slugs() -> list[str]:
    return sorted(PLATFORMS.keys())
