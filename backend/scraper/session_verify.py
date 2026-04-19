"""Headless checks that a saved Playwright profile appears logged in (not on a login screen)."""

from __future__ import annotations

from typing import Optional

from backend.scraper.urls import LOGIN_START_URLS

# URLs to open after session exists; if we remain on or redirect to login, session is invalid.
_PROBE_URLS: dict[str, str] = {
    "linkedin": "https://www.linkedin.com/feed/",
    "apollo": "https://app.apollo.io/#/people",
    "upwork": "https://www.upwork.com/nx/find-work/",
    "fiverr": "https://www.fiverr.com/",
    "clutch": "https://clutch.co/",
    "crunchbase": "https://www.crunchbase.com/discover/",
    "wellfound": "https://wellfound.com/",
    "google_maps": "https://www.google.com/maps",
    "justdial": "https://www.justdial.com/",
    "other": "",
}


def _looks_like_login(url: str, slug: str) -> bool:
    u = (url or "").lower()
    if "login" in u or "signin" in u or "sign-in" in u:
        return True
    if slug == "linkedin" and ("uas/login" in u or "checkpoint" in u):
        return True
    if slug == "apollo" and "#/login" in u:
        return True
    return False


def verify_playwright_session(slug: str, *, custom_login_url: Optional[str] = None) -> bool:
    """
    Launch headless persistent context; open probe URL (or custom base URL).
    Returns True only if navigation does not land on an obvious login URL.
    """
    from playwright.sync_api import sync_playwright

    from backend.scraper.session_manager import SessionManager

    s = slug.strip().lower().replace(" ", "_")
    sm = SessionManager()
    root = sm.path_for(s)
    if not root.is_dir():
        return False

    probe = _PROBE_URLS.get(s) or ""
    if not probe and custom_login_url:
        probe = custom_login_url.strip()
    if not probe:
        probe = LOGIN_START_URLS.get(s) or custom_login_url or ""
    if not probe:
        return False

    user_dir = str(root)
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(probe, wait_until="domcontentloaded", timeout=45_000)
                final_url = page.url or ""
                bad = _looks_like_login(final_url, s)
                return not bad
            finally:
                ctx.close()
    except Exception:
        return False
