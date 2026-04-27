from __future__ import annotations

from typing import Any, ClassVar, Dict, List
from urllib.parse import quote_plus

import config as app_config
from playwright.sync_api import Page

from backend.scraper.base import BaseScraper
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Standard (free) LinkedIn people search — not Sales Navigator.
_JS_EXTRACT = r"""
() => {
  const badHref = (href) => {
    const h = (href || '').toLowerCase();
    return (
      h.includes('/company/') ||
      h.includes('/school/') ||
      h.includes('/showcase/') ||
      h.includes('/learning/') ||
      h.includes('/pub/dir/')
    );
  };

  const normalizeUrl = (href) => {
    try {
      const u = new URL(href, 'https://www.linkedin.com');
      const parts = u.pathname.split('/').filter(Boolean);
      const i = parts.indexOf('in');
      if (i < 0 || i + 1 >= parts.length) return null;
      const slug = parts[i + 1];
      if (!slug) return null;
      return 'https://www.linkedin.com/in/' + decodeURIComponent(slug);
    } catch (e) {
      return null;
    }
  };

  const anchors = Array.from(document.querySelectorAll('a[href*="/in/"]'));
  const seen = new Set();
  const out = [];

  for (const a of anchors) {
    if (badHref(a.href)) continue;
    const canon = normalizeUrl(a.href);
    if (!canon) continue;
    const key = canon.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);

    let name = (a.innerText || '').trim().replace(/\s+/g, ' ');
    const container =
      a.closest('[data-chameleon-result-urn*="fsd_profile"]') ||
      a.closest('li') ||
      a.closest('div[data-view-name]') ||
      a.closest('article');

    if ((!name || name.length < 2) && container) {
      const lines = (container.innerText || '')
        .split('\n')
        .map((x) => x.trim())
        .filter(Boolean);
      if (lines.length) name = lines[0].slice(0, 200);
    }

    let title = '';
    let company = '';
    if (container) {
      const lines = (container.innerText || '')
        .split('\n')
        .map((x) => x.trim())
        .filter(Boolean);
      const headline = (lines.length > 1 ? lines[1] : '') || '';
      const lowerH = headline.toLowerCase();
      const atPos = lowerH.lastIndexOf(' at ');
      if (atPos > 0) {
        title = headline.slice(0, atPos).trim().slice(0, 220);
        company = headline.slice(atPos + 4).trim().split(/[·|]/)[0].trim().slice(0, 220);
      } else {
        title = headline.slice(0, 220);
      }
      if (!company && lines.length > 2) {
        const third = (lines[2] || '').split(/[·|]/)[0].trim();
        if (third && !/^[\d\s]+$/.test(third)) company = third.slice(0, 220);
      }
    }

    let location = '';
    if (container) {
      const lines = (container.innerText || '')
        .split('\n')
        .map((x) => x.trim())
        .filter(Boolean);
      for (let j = 2; j < Math.min(lines.length, 6); j++) {
        const t = lines[j] || '';
        if (!t) continue;
        if (t.toLowerCase().includes(' at ')) continue;
        if (t.length > 1 && t.length < 120 && !/^connect$/i.test(t) && !/^message$/i.test(t)) {
          location = t.slice(0, 200);
          break;
        }
      }
    }

    out.push({
      linkedin_url: canon,
      url: canon,
      dedupe_key: canon,
      full_name: name || 'Unknown',
      title,
      company_name: company,
      location,
    });
  }
  return out;
}
"""

# Public profile / overlay: mailto and tel links when member chose to expose them.
_PROFILE_CONTACT_JS = r"""
() => {
  const emails = [];
  const phones = [];
  for (const a of document.querySelectorAll('a[href^="mailto:"], a[href^="MAILTO:"]')) {
    const raw = (a.getAttribute('href') || '').slice(7).split('?')[0].trim();
    if (raw.includes('@')) emails.push(decodeURIComponent(raw));
  }
  for (const a of document.querySelectorAll('a[href^="tel:"], a[href^="TEL:"]')) {
    const t = (a.getAttribute('href') || '').slice(4).split('?')[0].trim();
    if (t) phones.push(decodeURIComponent(t));
  }
  return { email: emails[0] || '', phone: phones[0] || '' };
}
"""


class LinkedInScraper(BaseScraper):
    slug: ClassVar[str] = "linkedin"

    def filter_query_string(self) -> str:
        """LinkedIn ignores our generic ``country=`` query params; filters are folded into ``keywords``."""
        return ""

    def _linkedin_keywords(self) -> str:
        """Single search box: keyword + location + industry + company size (deduped)."""
        parts: list[str] = []
        blob = ""

        def push(s: str) -> None:
            nonlocal blob
            t = (s or "").strip()
            if not t:
                return
            low = blob.lower()
            if t.lower() in low:
                return
            parts.append(t)
            blob = (blob + " " + t).strip()

        push(self.cfg.keyword)
        push(self.cfg.country)
        push(self.cfg.industry)
        push(self.cfg.company_size)
        return " ".join(parts)[:450]

    def build_search_url(self) -> str:
        kw = quote_plus(self._linkedin_keywords())
        # Free / basic LinkedIn: main people search (not Sales Navigator).
        return (
            f"https://www.linkedin.com/search/results/people/?keywords={kw}&origin=GLOBAL_SEARCH_HEADER"
        )

    def enrich_collected_profiles(self, page: Page, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not getattr(self.cfg, "profile_contact_enrich", False) or not rows:
            return rows
        cap = min(
            len(rows),
            max(0, int(getattr(app_config, "SCRAPER_PROFILE_ENRICH_CAP", 8) or 0)),
            int(self.cfg.max_leads or 20),
        )
        if cap <= 0:
            return rows
        out: List[Dict[str, Any]] = []
        for i, row in enumerate(rows):
            if i >= cap:
                out.append(row)
                continue
            url = str(row.get("linkedin_url") or row.get("url") or "").strip()
            if not url or "/in/" not in url.lower():
                out.append(row)
                continue
            self._progress.phase(
                "extracting_data",
                message=f"Opening profile {i + 1}/{cap} for public contact links",
                page=i + 1,
                leads_found=len(out) + 1,
            )
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                self.delay.between_actions()
                data = page.evaluate(_PROFILE_CONTACT_JS)
                if isinstance(data, dict):
                    em = str(data.get("email") or "").strip()
                    ph = str(data.get("phone") or "").strip()
                    if em:
                        row["email"] = em[:320]
                    if ph:
                        row["phone"] = ph[:64]
            except Exception as e:
                logger.info("LinkedIn profile enrich skipped for %s: %s", url, e)
            out.append(row)
        return out

    def scroll_results_container(self, page: Page) -> None:
        """LinkedIn scrolls the center column, not always ``document.body``."""
        page.evaluate(
            r"""() => {
          const selectors = [
            '.scaffold-layout__list-container',
            '.scaffold-layout__list',
            'main.scaffold-layout__list',
            '.search-results-container',
            'div.search-results-container',
            'main[role="main"]',
          ];
          for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.scrollHeight > el.clientHeight + 80) {
              el.scrollBy(0, Math.min(1000, Math.max(300, el.scrollHeight / 6)));
              return;
            }
          }
          window.scrollBy(0, Math.min(1200, Math.max(200, document.body.scrollHeight / 5)));
        }"""
        )

    def extract_from_page(self, page: Page) -> List[Dict[str, Any]]:
        try:
            page.wait_for_load_state("load", timeout=20_000)
        except Exception:
            pass
        try:
            page.wait_for_selector("main a[href*='/in/'], a[href*='/in/']", timeout=25_000)
        except Exception:
            logger.warning(
                "LinkedIn search: no profile links found in DOM yet (login wall, empty results, or slow render)."
            )

        try:
            raw = page.evaluate(_JS_EXTRACT)
        except Exception as e:
            logger.warning("LinkedIn extract script failed: %s", e)
            return []

        if not isinstance(raw, list):
            return []

        rows: List[Dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            url = str(item.get("linkedin_url") or item.get("url") or "").strip()
            if "/in/" not in url:
                continue
            name = str(item.get("full_name") or "").strip() or "Unknown"
            rows.append(
                {
                    "linkedin_url": url,
                    "url": url,
                    "dedupe_key": url,
                    "full_name": name,
                    "title": str(item.get("title") or "").strip(),
                    "company_name": str(item.get("company_name") or "").strip(),
                    "location": str(item.get("location") or "").strip(),
                }
            )

        if not rows:
            logger.info("LinkedIn extract: 0 rows this pass (selectors or visibility).")
        return rows
