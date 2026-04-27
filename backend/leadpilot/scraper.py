"""
LinkedIn extraction entry — delegates to `lead_scraper.collect_linkedin_leads`.
Selenium details stay in the parent module and `scraper_core` to avoid duplicating selectors.
"""

from __future__ import annotations

from .lead_scraper import collect_linkedin_leads

__all__ = ["collect_linkedin_leads", "scrape_for_leads"]


def scrape_for_leads(
    max_leads: int | None,
    *,
    ask_limit: bool = False,
) -> list[dict]:
    """Return raw dict rows from LinkedIn (enrichment not applied)."""
    if ask_limit:
        return collect_linkedin_leads(ask_limit_after_browser_ready=True)
    return collect_linkedin_leads(
        max_leads, ask_limit_after_browser_ready=False
    )
