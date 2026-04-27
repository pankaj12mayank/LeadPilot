# Runtime-disabled platform (LinkedIn-only registry in backend/scraper/registry.py). Kept for future use.
from __future__ import annotations

from typing import Any, ClassVar, Dict, List
from urllib.parse import quote_plus

from playwright.sync_api import Page

from backend.scraper.base import BaseScraper


class ClutchScraper(BaseScraper):
    slug: ClassVar[str] = "clutch"

    def build_search_url(self) -> str:
        kw = quote_plus(self.cfg.keyword)
        return f"https://clutch.co/search?query={kw}{self.filter_query_string()}"

    def extract_from_page(self, page: Page) -> List[Dict[str, Any]]:
        return []
