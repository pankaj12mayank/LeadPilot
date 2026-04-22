from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List
from urllib.parse import quote_plus

from playwright.sync_api import Page, sync_playwright

from backend.scraper.config import ScraperRunConfig, ScraperRunResult
from backend.scraper.delay_manager import DelayManager
from backend.scraper.exceptions import SessionMissingError
from backend.scraper.progress import JobProgressSink, NullProgressSink
from backend.scraper.raw_lead_saver import RawLeadSaver
from backend.scraper.session_manager import SessionManager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class BaseScraper(ABC):
    """
    Playwright sync scraper template: persistent session, random delays, scroll + extract loop.

    Subclasses implement ``build_search_url`` and ``extract_from_page`` (selectors per site).
    Platform-specific search URLs live in ``backend/scraper/platforms/<slug>.py``.
    """

    slug: ClassVar[str]

    def __init__(
        self,
        cfg: ScraperRunConfig,
        *,
        delay: DelayManager | None = None,
        sessions: SessionManager | None = None,
        saver: RawLeadSaver | None = None,
        progress: JobProgressSink | NullProgressSink | None = None,
    ) -> None:
        self.cfg = cfg
        self.delay = delay or DelayManager.from_config(cfg)
        self.sessions = sessions or SessionManager()
        self.saver = saver or RawLeadSaver()
        self._progress = progress or NullProgressSink()

    @abstractmethod
    def build_search_url(self) -> str:
        """Landing URL for keyword + filters (logged-in session required)."""

    def filter_query_string(self) -> str:
        """Append-only filter hints for URLs (platform-specific parsers may ignore)."""
        parts: list[str] = []
        if self.cfg.country:
            parts.append(f"country={quote_plus(self.cfg.country)}")
        if self.cfg.industry:
            parts.append(f"industry={quote_plus(self.cfg.industry)}")
        if self.cfg.company_size:
            parts.append(f"company_size={quote_plus(self.cfg.company_size)}")
        return ("&" + "&".join(parts)) if parts else ""

    def extract_from_page(self, page: Page) -> List[Dict[str, Any]]:
        """Parse visible results into raw dicts. Override per platform."""
        return []

    def scroll_results_container(self, page: Page) -> None:
        """Scroll the primary results list (override when the site scrolls an inner panel)."""
        page.evaluate(
            "window.scrollBy(0, Math.min(1200, Math.max(200, document.body.scrollHeight / 5)))"
        )

    def enrich_collected_profiles(self, page: Page, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optional second pass (e.g. open profiles for public contact links). Override per platform."""
        return rows

    def run(self) -> ScraperRunResult:
        run_id = RawLeadSaver.new_run_id()
        errors: List[str] = []
        collected: List[Dict[str, Any]] = []
        dupes_skipped = 0
        total_seen = 0

        if not self.sessions.has_session(self.slug):
            raise SessionMissingError(
                f"No persisted browser profile for '{self.slug}'. "
                f"Call POST /scraper/sessions/{self.slug}/manual-login first.",
                platform=self.slug,
            )

        user_dir = str(self.sessions.user_data_dir(self.slug))
        try:
            self._progress.phase(
                "searching",
                message=f"Launching browser for {self.slug}",
                page=0,
                leads_found=0,
                duplicates_removed=0,
            )
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_dir,
                    headless=self.cfg.headless,
                    args=["--disable-blink-features=AutomationControlled"],
                    viewport={"width": 1366, "height": 900},
                )
                try:
                    page = ctx.pages[0] if ctx.pages else ctx.new_page()
                    self.delay.between_actions()
                    url = self.build_search_url()
                    self._progress.phase("searching", message=f"Navigating to search URL", page=1)
                    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
                    self.delay.between_actions()

                    seen: set[str] = set()
                    for round_idx in range(self.cfg.max_scroll_rounds):
                        self._progress.phase(
                            "searching",
                            message=f"Scraping visible result cards (scroll {round_idx + 1}/{self.cfg.max_scroll_rounds})",
                            page=round_idx + 1,
                            leads_found=len(collected),
                            duplicates_removed=dupes_skipped,
                        )
                        self.delay.between_actions()
                        batch = self.extract_from_page(page)
                        for row in batch:
                            total_seen += 1
                            self._progress.phase(
                                "extracting_data",
                                message="Extracting card fields",
                                page=round_idx + 1,
                                leads_found=len(collected),
                                duplicates_removed=dupes_skipped,
                            )
                            key = str(
                                row.get("dedupe_key")
                                or row.get("url")
                                or row.get("linkedin_url")
                                or row.get("name")
                                or json.dumps(row, sort_keys=True, default=str)[:240]
                            )
                            if key in seen:
                                dupes_skipped += 1
                                self._progress.phase(
                                    "extracting_data",
                                    message="Duplicate card skipped",
                                    leads_found=len(collected),
                                    duplicates_removed=dupes_skipped,
                                )
                                continue
                            seen.add(key)
                            row.setdefault("source_platform", self.slug)
                            row.setdefault("search_keyword", self.cfg.keyword)
                            row.setdefault("filter_country", self.cfg.country)
                            row.setdefault("filter_industry", self.cfg.industry)
                            row.setdefault("filter_company_size", self.cfg.company_size)
                            collected.append(row)
                            self._progress.lead_added(row, len(collected))
                            if len(collected) >= int(self.cfg.max_leads or 20):
                                break
                        if len(collected) >= int(self.cfg.max_leads or 20):
                            break
                        self.scroll_results_container(page)
                        self.delay.short_jitter()
                    collected = self.enrich_collected_profiles(page, collected)
                finally:
                    try:
                        ctx.close()
                    except Exception:
                        logger.warning("Playwright context close failed", exc_info=True)
        except SessionMissingError:
            raise
        except Exception as e:
            logger.exception("Scraper failure [%s]: %s", self.slug, e)
            errors.append(str(e))

        final_rows = collected[: int(self.cfg.max_leads or 20)]
        self._progress.phase(
            "saving_lead",
            message=f"Writing {len(final_rows)} rows to database and CSV",
            leads_found=len(final_rows),
            duplicates_removed=dupes_skipped,
        )
        csv_path: str | None = None
        try:
            csv_path = self.saver.save_run(
                run_id=run_id,
                platform=self.slug,
                keyword=self.cfg.keyword,
                country=self.cfg.country,
                industry=self.cfg.industry,
                company_size=self.cfg.company_size,
                rows=final_rows,
            )
        except Exception as e:
            logger.exception("Raw save failed: %s", e)
            errors.append(f"save_failed: {e}")

        self._progress.phase(
            "completed",
            message="Scrape finished",
            leads_found=len(final_rows),
            duplicates_removed=dupes_skipped,
        )

        return ScraperRunResult(
            run_id=run_id,
            platform=self.slug,
            collected=len(final_rows),
            csv_path=csv_path,
            errors=errors,
            total_found=int(total_seen),
            saved=len(final_rows),
            duplicates_removed=int(dupes_skipped),
        )
