"""Public company ingestion from source pages (small-batch, delayed, non-aggressive)."""

from __future__ import annotations

import re
import time
from typing import Callable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from backend.services.company_service import normalize_company_domain, normalize_company_source

SUPPORTED_REAL_SOURCES = frozenset(
    {
        "manual",
        "job_board",
        "yc",
        "crunchbase",
        "local",
        "builtwith",
    }
)

_BAD_HOST_PARTS = (
    "linkedin.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "wikipedia.org",
    "github.com",
    "medium.com",
    "reddit.com",
)

_WS_RE = re.compile(r"\s+")


def _guess_name_from_domain(domain: str) -> str:
    if not domain:
        return ""
    left = domain.split(".", 1)[0]
    left = re.sub(r"[^a-z0-9\-]", " ", left.lower())
    left = _WS_RE.sub(" ", left.replace("-", " ")).strip()
    return left.title() if left else domain


def _extract_company_candidates_from_html(html: str, page_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "").strip()
        if not href:
            continue
        abs_url = urljoin(page_url, href)
        p = urlparse(abs_url)
        if p.scheme not in ("http", "https"):
            continue
        host = (p.netloc or "").lower()
        if not host:
            continue
        if any(bad in host for bad in _BAD_HOST_PARTS):
            continue
        dom = normalize_company_domain(abs_url)
        if not dom or dom in seen:
            continue
        seen.add(dom)
        txt = _WS_RE.sub(" ", (a.get_text(" ", strip=True) or "")).strip()
        name = txt or _guess_name_from_domain(dom)
        out.append({"company_name": name, "website": f"https://{dom}"})
    return out


def _default_fetch_html(url: str, *, timeout: float = 18.0) -> str:
    import httpx

    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "LeadPilotCompanyIngest/1.0"},
    ) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text or ""


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def collect_companies_from_source_pages(
    *,
    source: str,
    seed_urls: list[str],
    batch_size: int = 10,
    delay_seconds: float = 1.0,
    max_companies: int = 200,
    fetch_html: Callable[[str], str] | None = None,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """
    Collect company candidates from provided source pages.

    - Processes seed URLs in small batches (10-20 recommended).
    - Sleeps between requests to avoid aggressive behavior.
    - Keeps only rows with a valid website/domain.
    """
    raw_src = (source or "").strip().lower().replace("-", "_")
    src = normalize_company_source(raw_src)
    if raw_src:
        src = raw_src
    if src not in SUPPORTED_REAL_SOURCES:
        raise ValueError(f"Unsupported source: {source}")

    fetch = fetch_html or _default_fetch_html
    bs = max(10, min(20, int(batch_size or 10)))
    delay = max(0.2, min(float(delay_seconds or 1.0), 8.0))
    limit = max(1, min(int(max_companies or 200), 2000))

    cleaned = [u.strip() for u in seed_urls if str(u or "").strip()]
    out: list[dict[str, str]] = []
    seen_dom: set[str] = set()
    stats = {"pages_ok": 0, "pages_failed": 0, "candidates": 0}

    for group in _chunks(cleaned, bs):
        for idx, page_url in enumerate(group):
            try:
                html = fetch(page_url)
                stats["pages_ok"] += 1
            except Exception:
                stats["pages_failed"] += 1
                if idx < len(group) - 1:
                    time.sleep(delay)
                continue
            for row in _extract_company_candidates_from_html(html, page_url):
                dom = normalize_company_domain(row.get("website"))
                if not dom or dom in seen_dom:
                    continue
                seen_dom.add(dom)
                out.append(
                    {
                        "company_name": str(row.get("company_name") or "").strip() or _guess_name_from_domain(dom),
                        "website": str(row.get("website") or "").strip(),
                        "source": src,
                    }
                )
                if len(out) >= limit:
                    stats["candidates"] = len(out)
                    return out, stats
            if idx < len(group) - 1:
                time.sleep(delay)
        # extra pause between batches
        time.sleep(delay)
    stats["candidates"] = len(out)
    return out, stats


def default_seed_urls_for_source(*, source: str, keyword: str, location: str = "") -> list[str]:
    """
    Build lightweight public listing/search URLs per source for Explorer retries.
    """
    src = (source or "").strip().lower().replace("-", "_")
    kw = (keyword or "").strip().replace(" ", "+")
    loc = (location or "").strip().replace(" ", "+")
    q = "+".join([x for x in (kw, loc) if x]) or "software"
    if src == "yc":
        return [f"https://www.ycombinator.com/companies?query={q}"]
    if src == "job_board":
        return [
            f"https://wellfound.com/discover/companies?query={q}",
            f"https://www.indeed.com/companies/search?q={q}",
        ]
    if src == "crunchbase":
        return [f"https://www.crunchbase.com/discover/organization.companies/field/organizations/categories/{q}"]
    if src == "local":
        return [f"https://www.google.com/search?q={q}+company+official+site"]
    if src == "builtwith":
        return [f"https://trends.builtwith.com/websitelist/{q}"]
    return []
