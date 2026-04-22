"""Playwright persistent browser context for manual login and single-lead capture."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

import config
from backend.utils.safe_capture_logging import get_safe_capture_logger

_log = get_safe_capture_logger("browser")


@dataclass
class CaptureBrowser:
    """Owns sync Playwright + persistent context (Chrome channel when available)."""

    playwright: Playwright
    context: BrowserContext

    @property
    def default_page(self) -> Page:
        pages = self.context.pages
        if pages:
            return pages[-1]
        return self.context.new_page()

    def close(self) -> None:
        try:
            self.context.close()
        except Exception as e:
            _log.warning("context.close failed: %s", e)
        try:
            self.playwright.stop()
        except Exception as e:
            _log.warning("playwright.stop failed: %s", e)


def launch_capture_browser(
    *,
    user_data_dir: str | None = None,
    headless: bool = False,
) -> CaptureBrowser:
    """
    Launch a **persistent** Chromium/Chrome profile directory.

    No automatic navigation to login pages — the user drives the browser manually.
    """
    profile = Path(user_data_dir or config.SAFE_CAPTURE_PROFILE_DIR)
    profile.mkdir(parents=True, exist_ok=True)

    pw = sync_playwright().start()
    try:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=os.fspath(profile),
            channel="chrome",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 860},
        )
    except Exception as e:
        _log.warning("Chrome channel unavailable (%s); falling back to bundled Chromium.", e)
        context = pw.chromium.launch_persistent_context(
            user_data_dir=os.fspath(profile),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 860},
        )

    _log.info("Persistent capture browser started (profile=%s).", profile)
    return CaptureBrowser(playwright=pw, context=context)
