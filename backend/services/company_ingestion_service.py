"""Public company ingestion from source pages (small-batch, delayed, non-aggressive)."""

from __future__ import annotations

import re
import time
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from backend.services import company_service, runtime_settings
from backend.services.company_service import normalize_company_domain, normalize_company_source
from backend.utils.logger import get_logger

logger = get_logger(__name__)

SUPPORTED_REAL_SOURCES = frozenset(
    {
        "manual",
        "linkedin",
        "job_board",
        "yc",
        "crunchbase",
        "local",
        "builtwith",
        "google_maps",
        "indiamart",
        "justdial",
        "eworldtrade",
        "global_sources",
        "thomasnet",
        "yelp",
        "faire",
    }
)
MARKETPLACE_SOURCES = frozenset(
    {
        "google_maps",
        "indiamart",
        "justdial",
        "eworldtrade",
        "global_sources",
        "thomasnet",
        "yelp",
        "faire",
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
_COMPANY_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _guess_name_from_domain(domain: str) -> str:
    if not domain:
        return ""
    left = domain.split(".", 1)[0]
    left = re.sub(r"[^a-z0-9\-]", " ", left.lower())
    left = _WS_RE.sub(" ", left.replace("-", " ")).strip()
    return left.title() if left else domain


def _normalize_company_token(value: str) -> str:
    return _COMPANY_TOKEN_RE.sub(" ", str(value or "").strip().lower()).strip()


def _quality_stats_template() -> dict[str, int]:
    return {
        "missing_website": 0,
        "duplicate_domain": 0,
        "invalid_url": 0,
        "short_content": 0,
    }


def _passes_content_length(value: str, *, min_content_length: int) -> bool:
    if min_content_length <= 0:
        return True
    return len(_WS_RE.sub(" ", str(value or "").strip())) >= min_content_length


def _apply_quality_filters(
    rows: list[dict[str, Any]],
    *,
    source: str,
    seen_domains: set[str] | None = None,
    min_content_length: int = 0,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    src = normalize_company_source(source)
    out: list[dict[str, str]] = []
    local_seen = seen_domains if seen_domains is not None else set()
    stats = _quality_stats_template()
    for raw in rows:
        if not isinstance(raw, dict):
            stats["invalid_url"] += 1
            continue
        website = str(raw.get("website") or raw.get("domain") or "").strip()
        if not website:
            stats["missing_website"] += 1
            continue
        domain = normalize_company_domain(website)
        if not domain:
            stats["invalid_url"] += 1
            continue
        if domain in local_seen:
            stats["duplicate_domain"] += 1
            continue
        company_name = str(raw.get("company_name") or raw.get("name") or "").strip() or _guess_name_from_domain(domain)
        content_basis = str(raw.get("content_text") or raw.get("raw_text") or company_name).strip()
        if not _passes_content_length(content_basis, min_content_length=min_content_length):
            stats["short_content"] += 1
            continue
        local_seen.add(domain)
        normalized = {
            "company_name": company_name,
            "website": f"https://{domain}",
            "source": src,
        }
        contact = str(raw.get("contact") or "").strip()
        if contact:
            normalized["contact"] = contact
        out.append(normalized)
    return out, stats


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


def _extract_job_board_company_names(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    candidates: list[str] = []
    seen: set[str] = set()
    selectors = [
        "[data-company-name]",
        "[data-testid='company-name']",
        ".company-name",
        ".companyName",
        ".job-company",
        "a[data-tn-element='companyName']",
    ]
    for selector in selectors:
        for node in soup.select(selector):
            text = _WS_RE.sub(" ", node.get_text(" ", strip=True)).strip()
            key = _normalize_company_token(text)
            if len(key) < 2 or key in seen:
                continue
            seen.add(key)
            candidates.append(text)
    if candidates:
        return candidates

    for node in soup.find_all(["a", "span", "div"]):
        text = _WS_RE.sub(" ", node.get_text(" ", strip=True)).strip()
        key = _normalize_company_token(text)
        if len(key) < 3 or key in seen:
            continue
        lower = key.lower()
        if any(token in lower for token in ["apply", "remote", "full time", "part time", "job", "role", "salary"]):
            continue
        if len(text.split()) > 6:
            continue
        seen.add(key)
        candidates.append(text)
    return candidates[:50]


def _extract_startup_directory_companies(html: str, page_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    out: list[dict[str, str]] = []
    seen_domains: set[str] = set()
    page_domain = normalize_company_domain(page_url)

    selectors = [
        "[data-company-url]",
        "[data-website]",
        ".company-card a[href]",
        ".startup-card a[href]",
        ".directory-item a[href]",
        "a.company-link[href]",
    ]
    for selector in selectors:
        for node in soup.select(selector):
            href = str(node.get("data-company-url") or node.get("data-website") or node.get("href") or "").strip()
            if not href:
                continue
            abs_url = urljoin(page_url, href)
            domain = normalize_company_domain(abs_url)
            if not domain or domain == page_domain:
                continue
            if any(bad in domain for bad in _BAD_HOST_PARTS):
                continue
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            text = _WS_RE.sub(" ", node.get_text(" ", strip=True)).strip()
            name = text or _guess_name_from_domain(domain)
            out.append({"company_name": name, "website": f"https://{domain}"})
    if out:
        return out

    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "").strip()
        if not href:
            continue
        abs_url = urljoin(page_url, href)
        domain = normalize_company_domain(abs_url)
        if not domain or domain == page_domain or domain in seen_domains:
            continue
        text = _WS_RE.sub(" ", a.get_text(" ", strip=True)).strip()
        if len(text.split()) > 8:
            continue
        if any(bad in domain for bad in _BAD_HOST_PARTS):
            continue
        seen_domains.add(domain)
        out.append({"company_name": text or _guess_name_from_domain(domain), "website": f"https://{domain}"})
    return out


def _extract_local_business_companies(html: str, page_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    out: list[dict[str, str]] = []
    seen_domains: set[str] = set()
    selectors = [
        "[data-business-name][data-website]",
        ".business-card a[href]",
        ".local-result a[href]",
        ".listing a[href]",
    ]
    for selector in selectors:
        for node in soup.select(selector):
            href = str(node.get("data-website") or node.get("href") or "").strip()
            if not href:
                continue
            abs_url = urljoin(page_url, href)
            domain = normalize_company_domain(abs_url)
            if not domain or domain in seen_domains:
                continue
            if any(bad in domain for bad in _BAD_HOST_PARTS):
                continue
            seen_domains.add(domain)
            name = str(node.get("data-business-name") or "").strip()
            text = _WS_RE.sub(" ", node.get_text(" ", strip=True)).strip()
            out.append({"company_name": name or text or _guess_name_from_domain(domain), "website": f"https://{domain}"})
    if out:
        return out

    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "").strip()
        abs_url = urljoin(page_url, href)
        domain = normalize_company_domain(abs_url)
        if not domain or domain in seen_domains:
            continue
        if any(bad in domain for bad in _BAD_HOST_PARTS):
            continue
        text = _WS_RE.sub(" ", a.get_text(" ", strip=True)).strip()
        if len(text.split()) > 8:
            continue
        seen_domains.add(domain)
        out.append({"company_name": text or _guess_name_from_domain(domain), "website": f"https://{domain}"})
    return out


def _lookup_company_website(company_name: str, *, fetch_html: Callable[[str], str] | None = None) -> str:
    fetch = fetch_html or _default_fetch_html
    query = str(company_name or "").strip().replace(" ", "+")
    if not query:
        return ""
    search_url = f"https://www.google.com/search?q={query}+official+site"
    try:
        html = fetch(search_url)
    except Exception:
        return ""
    rows = _extract_company_candidates_from_html(html, search_url)
    for row in rows:
        candidate_name = str(row.get("company_name") or "").strip()
        if not candidate_name:
            continue
        if _normalize_company_token(company_name) in _normalize_company_token(candidate_name) or _normalize_company_token(candidate_name) in _normalize_company_token(company_name):
            return str(row.get("website") or "").strip()
    return str(rows[0].get("website") or "").strip() if rows else ""


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


def _normalize_adapter_rows(rows: list[dict[str, Any]], *, source: str) -> list[dict[str, str]]:
    cleaned, _stats = _apply_quality_filters(rows, source=source)
    return cleaned


def _run_source_pages(
    source: str,
    source_input: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    fetch = source_input.get("fetch_html") if callable(source_input.get("fetch_html")) else None
    cleaned = [str(u).strip() for u in (source_input.get("seed_urls") or []) if str(u).strip()]
    bs = max(10, min(20, int(source_input.get("batch_size") or 10)))
    delay = max(0.2, min(float(source_input.get("delay_seconds") or 1.0), 8.0))
    limit = max(1, min(int(source_input.get("max_companies") or 200), 2000))
    min_content_length = max(0, min(int(source_input.get("min_content_length") or 0), 1000))

    out: list[dict[str, str]] = []
    seen_dom: set[str] = set()
    stats = {"pages_ok": 0, "pages_failed": 0, "candidates": 0, **_quality_stats_template()}

    for group in _chunks(cleaned, bs):
        for idx, page_url in enumerate(group):
            try:
                html = (fetch or _default_fetch_html)(page_url)
                stats["pages_ok"] += 1
            except Exception:
                stats["pages_failed"] += 1
                if idx < len(group) - 1:
                    time.sleep(delay)
                continue
            filtered_rows, quality = _apply_quality_filters(
                _extract_company_candidates_from_html(html, page_url),
                source=source,
                seen_domains=seen_dom,
                min_content_length=min_content_length,
            )
            for key, value in quality.items():
                stats[key] += value
            for row in filtered_rows:
                out.append(row)
                if len(out) >= limit:
                    stats["candidates"] = len(out)
                    return out, stats
            if idx < len(group) - 1:
                time.sleep(delay)
        time.sleep(delay)
    stats["candidates"] = len(out)
    return out, stats


def _run_startup_directory_source(
    source: str,
    source_input: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    fetch = source_input.get("fetch_html") if callable(source_input.get("fetch_html")) else None
    cleaned = [str(u).strip() for u in (source_input.get("seed_urls") or []) if str(u).strip()]
    keyword = str(source_input.get("keyword") or "").strip()
    location = str(source_input.get("location") or "").strip()
    if not cleaned:
        cleaned = default_seed_urls_for_source(source=source, keyword=keyword, location=location)
    bs = max(1, min(5, int(source_input.get("batch_size") or 3)))
    delay = max(0.2, min(float(source_input.get("delay_seconds") or 1.0), 8.0))
    limit = max(1, min(int(source_input.get("max_companies") or 50), 500))
    min_content_length = max(0, min(int(source_input.get("min_content_length") or 0), 1000))

    out: list[dict[str, str]] = []
    seen_dom: set[str] = set()
    stats = {"pages_ok": 0, "pages_failed": 0, "candidates": 0, **_quality_stats_template()}

    for group in _chunks(cleaned, bs):
        for idx, page_url in enumerate(group):
            try:
                html = (fetch or _default_fetch_html)(page_url)
                stats["pages_ok"] += 1
            except Exception:
                stats["pages_failed"] += 1
                if idx < len(group) - 1:
                    time.sleep(delay)
                continue
            filtered_rows, quality = _apply_quality_filters(
                _extract_startup_directory_companies(html, page_url),
                source=source,
                seen_domains=seen_dom,
                min_content_length=min_content_length,
            )
            for key, value in quality.items():
                stats[key] += value
            for row in filtered_rows:
                out.append(row)
                if len(out) >= limit:
                    stats["candidates"] = len(out)
                    return out, stats
            if idx < len(group) - 1:
                time.sleep(delay)
        time.sleep(delay)
    stats["candidates"] = len(out)
    return out, stats


def _run_job_board_source(
    source: str,
    source_input: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    fetch = source_input.get("fetch_html") if callable(source_input.get("fetch_html")) else None
    keyword = str(source_input.get("keyword") or "").strip()
    location = str(source_input.get("location") or "").strip()
    cleaned = [str(u).strip() for u in (source_input.get("seed_urls") or []) if str(u).strip()]
    if not cleaned:
        cleaned = default_seed_urls_for_source(source=source, keyword=keyword, location=location)
    bs = max(1, min(5, int(source_input.get("batch_size") or 3)))
    delay = max(0.2, min(float(source_input.get("delay_seconds") or 1.0), 8.0))
    limit = max(1, min(int(source_input.get("max_companies") or 50), 200))
    min_content_length = max(0, min(int(source_input.get("min_content_length") or 0), 1000))
    stats = {"pages_ok": 0, "pages_failed": 0, "candidates": 0, **_quality_stats_template()}
    found: list[dict[str, str]] = []
    seen_domains: set[str] = set()
    seen_names: set[str] = set()

    for group in _chunks(cleaned, bs):
        for idx, page_url in enumerate(group):
            try:
                html = (fetch or _default_fetch_html)(page_url)
                stats["pages_ok"] += 1
            except Exception:
                stats["pages_failed"] += 1
                if idx < len(group) - 1:
                    time.sleep(delay)
                continue
            company_names = _extract_job_board_company_names(html)
            for company_name in company_names:
                normalized_name = _normalize_company_token(company_name)
                if not normalized_name or normalized_name in seen_names:
                    continue
                seen_names.add(normalized_name)
                website = _lookup_company_website(company_name, fetch_html=fetch)
                filtered_rows, quality = _apply_quality_filters(
                    [{"company_name": company_name, "website": website}],
                    source=source,
                    seen_domains=seen_domains,
                    min_content_length=min_content_length,
                )
                for key, value in quality.items():
                    stats[key] += value
                for row in filtered_rows:
                    found.append(row)
                    if len(found) >= limit:
                        stats["candidates"] = len(found)
                        return found, stats
                time.sleep(delay)
            if idx < len(group) - 1:
                time.sleep(delay)
        time.sleep(delay)
    stats["candidates"] = len(found)
    return found, stats


def _run_local_business_source(
    source: str,
    source_input: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    fetch = source_input.get("fetch_html") if callable(source_input.get("fetch_html")) else None
    keyword = str(source_input.get("keyword") or "").strip()
    location = str(source_input.get("location") or "").strip()
    cleaned = [str(u).strip() for u in (source_input.get("seed_urls") or []) if str(u).strip()]
    if not cleaned:
        cleaned = default_seed_urls_for_source(source=source, keyword=keyword, location=location)
    bs = max(1, min(5, int(source_input.get("batch_size") or 3)))
    delay = max(0.2, min(float(source_input.get("delay_seconds") or 1.0), 8.0))
    limit = max(1, min(int(source_input.get("max_companies") or 25), 100))
    min_content_length = max(0, min(int(source_input.get("min_content_length") or 0), 1000))
    stats = {"pages_ok": 0, "pages_failed": 0, "candidates": 0, **_quality_stats_template()}
    found: list[dict[str, str]] = []
    seen_domains: set[str] = set()

    for group in _chunks(cleaned, bs):
        for idx, page_url in enumerate(group):
            try:
                html = (fetch or _default_fetch_html)(page_url)
                stats["pages_ok"] += 1
            except Exception:
                stats["pages_failed"] += 1
                if idx < len(group) - 1:
                    time.sleep(delay)
                continue
            filtered_rows, quality = _apply_quality_filters(
                _extract_local_business_companies(html, page_url),
                source=source,
                seen_domains=seen_domains,
                min_content_length=min_content_length,
            )
            for key, value in quality.items():
                stats[key] += value
            for row in filtered_rows:
                found.append(row)
                if len(found) >= limit:
                    stats["candidates"] = len(found)
                    return found, stats
            if idx < len(group) - 1:
                time.sleep(delay)
        time.sleep(delay)
    stats["candidates"] = len(found)
    return found, stats


def _run_marketplace_source(
    source: str,
    source_input: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """
    Generic marketplace/directory adapter wrapper.
    Keeps behavior safe and modular while allowing source-specific seeds.
    """
    keyword = str(source_input.get("keyword") or "").strip()
    location = str(source_input.get("location") or "").strip()
    cleaned = [str(u).strip() for u in (source_input.get("seed_urls") or []) if str(u).strip()]
    if not cleaned:
        cleaned = default_seed_urls_for_source(source=source, keyword=keyword, location=location)
    source_input = dict(source_input)
    source_input["seed_urls"] = cleaned
    return _run_source_pages(source, source_input)


def _safety_capped_source_input(source_input: dict[str, Any]) -> dict[str, Any]:
    cfg = runtime_settings.get_admin_config()
    safety = cfg.get("safety_control") or {}
    out = dict(source_input or {})
    requested_batch = int(out.get("batch_size") or 10)
    requested_delay = float(out.get("delay_seconds") or 1.0)
    requested_max = int(out.get("max_companies") or 200)
    cap_batch = max(1, min(int(safety.get("batch_size") or 10), 100))
    cap_delay = max(0.2, min(float(safety.get("delay_seconds") or 1.0), 8.0))
    cap_pages = max(1, min(int(safety.get("pagination_limit") or 50), 2000))
    out["batch_size"] = max(1, min(requested_batch, cap_batch))
    out["delay_seconds"] = max(0.2, min(requested_delay, cap_delay))
    out["max_companies"] = max(1, min(requested_max, cap_pages))
    return out


def _run_source_with_stats(source: str, source_input: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, int]]:
    src_input = _safety_capped_source_input(source_input)
    src = (source or "").strip().lower().replace("-", "_")
    if src == "job_board":
        return _run_job_board_source(src, src_input)
    if src == "local":
        return _run_local_business_source(src, src_input)
    if src in {"yc", "crunchbase", "builtwith", "linkedin"}:
        return _run_startup_directory_source(src, src_input)
    if src in MARKETPLACE_SOURCES:
        return _run_marketplace_source(src, src_input)
    return _run_source_pages(src, src_input)


def run_source(source: str, source_input: dict[str, Any]) -> list[dict[str, str]]:
    """
    Common adapter interface for all sources.

    Returns standardized company rows:
    - company_name
    - website (mandatory)
    - source
    """
    raw_src = (source or "").strip().lower().replace("-", "_")
    src = normalize_company_source(raw_src)
    if raw_src:
        src = raw_src
    registry_entry = runtime_settings.get_source_registry_entry(src)
    adapter_function = str((registry_entry or {}).get("adapter_function") or "").strip().lower()
    input_type = str((registry_entry or {}).get("input_type") or "").strip().lower()
    if src not in SUPPORTED_REAL_SOURCES and registry_entry is None:
        raise ValueError(f"Unsupported source: {source}")
    if not isinstance(source_input, dict):
        source_input = {}
    if input_type in {"csv", "file"} or adapter_function == "ingest_public_companies":
        raise ValueError(f"Source {source!r} expects CSV/manual ingestion, use /companies/ingest")
    if registry_entry is not None and src not in SUPPORTED_REAL_SOURCES:
        rows, _stats = _run_source_pages(src, _safety_capped_source_input(source_input))
        return _normalize_adapter_rows(rows, source=src)
    rows, _stats = _run_source_with_stats(src, source_input)
    return _normalize_adapter_rows(rows, source=src)


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def collect_companies_from_source_pages(
    *,
    source: str,
    seed_urls: list[str],
    batch_size: int = 10,
    delay_seconds: float = 1.0,
    max_companies: int = 200,
    min_content_length: int = 0,
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

    source_input = {
        "seed_urls": seed_urls,
        "batch_size": batch_size,
        "delay_seconds": delay_seconds,
        "max_companies": max_companies,
        "min_content_length": min_content_length,
        "fetch_html": fetch_html,
    }
    return _run_source_with_stats(src, source_input)


def ingest_from_source(
    *,
    db,
    source: str,
    source_input: dict[str, Any],
) -> dict[str, Any]:
    """
    Adapter -> Company DB flow.

    - Run source adapter
    - Normalize domain + source
    - Update ``last_updated`` when domain exists
    - Insert new row otherwise
    """
    rows, fetch_stats = _run_source_with_stats(source, source_input)
    rows = _normalize_adapter_rows(rows, source=source)
    save_stats = company_service.ingest_public_companies(db, rows, default_source=source)
    return {
        "fetched": fetch_stats,
        "saved": save_stats,
        "rows": rows,
    }


def ingest_from_sources(
    *,
    db,
    sources: list[str],
    source_input_factory: Callable[[str], dict[str, Any]] | None = None,
    shared_source_input: dict[str, Any] | None = None,
    delay_between_sources: float = 1.0,
) -> dict[str, Any]:
    """
    Sequential multi-source ingestion with per-source batching and delays.
    """
    requested_sources = [
        str(src or "").strip().lower().replace("-", "_")
        for src in (sources or [])
        if str(src or "").strip()
    ]
    unique_sources: list[str] = []
    seen_sources: set[str] = set()
    for src in requested_sources:
        if src == "manual" or src in seen_sources:
            continue
        seen_sources.add(src)
        unique_sources.append(src)

    source_delay = max(0.2, min(float(delay_between_sources or 1.0), 8.0))
    cfg = runtime_settings.get_admin_config()
    safety = cfg.get("safety_control") or {}
    if delay_between_sources is None:
        source_delay = max(0.2, min(float(safety.get("delay_seconds") or 1.0), 8.0))
    runs: list[dict[str, Any]] = []
    fetched_total = {"pages_ok": 0, "pages_failed": 0, "candidates": 0}
    saved_total = {"created": 0, "updated": 0, "skipped": 0}
    failed_sources = 0
    quality_skips_total = {"missing_website": 0, "duplicate_domain": 0, "invalid_url": 0, "short_content": 0}
    errors: list[dict[str, str]] = []

    logger.info("ingestion.multi_source.start sources=%s delay=%s", unique_sources, source_delay)
    for idx, src in enumerate(unique_sources):
        logger.info("ingestion.source.start source=%s index=%s/%s", src, idx + 1, len(unique_sources))
        try:
            source_input = dict(shared_source_input or {})
            if source_input_factory is not None:
                source_input.update(source_input_factory(src) or {})
            source_input["batch_size"] = int(source_input.get("batch_size") or safety.get("batch_size") or 10)
            source_input["delay_seconds"] = float(source_input.get("delay_seconds") or safety.get("delay_seconds") or 1.0)
            source_input["max_companies"] = int(source_input.get("max_companies") or safety.get("pagination_limit") or 200)
            source_input["max_companies"] = max(1, min(source_input["max_companies"], 2000))
            result = ingest_from_source(db=db, source=src, source_input=source_input)
            fetched = result.get("fetched") or {}
            saved = result.get("saved") or {}
            fetched_total["pages_ok"] += int(fetched.get("pages_ok") or 0)
            fetched_total["pages_failed"] += int(fetched.get("pages_failed") or 0)
            fetched_total["candidates"] += int(fetched.get("candidates") or 0)
            for key in quality_skips_total:
                quality_skips_total[key] += int(fetched.get(key) or 0)
            saved_total["created"] += int(saved.get("created") or 0)
            saved_total["updated"] += int(saved.get("updated") or 0)
            saved_total["skipped"] += int(saved.get("skipped") or 0)
            runs.append({"source": src, "status": "ok", **result})
            logger.info(
                "ingestion.source.done source=%s candidates=%s created=%s updated=%s skipped=%s",
                src,
                int(fetched.get("candidates") or 0),
                int(saved.get("created") or 0),
                int(saved.get("updated") or 0),
                int(saved.get("skipped") or 0),
            )
        except Exception as e:  # noqa: BLE001
            failed_sources += 1
            err = {"source": src, "stage": "adapter", "error": str(e)}
            errors.append(err)
            logger.warning("source_ingestion_failed source=%s stage=%s error=%s", src, "adapter", str(e))
            runs.append({"source": src, "status": "failed", "error": str(e)})
        if idx < len(unique_sources) - 1:
            time.sleep(source_delay)

    logger.info(
        "ingestion.multi_source.done total_sources=%s failed_sources=%s total_created=%s total_updated=%s total_skipped=%s",
        len(unique_sources),
        failed_sources,
        int(saved_total.get("created") or 0),
        int(saved_total.get("updated") or 0),
        int(saved_total.get("skipped") or 0),
    )
    return {
        "runs": runs,
        "fetched_total": fetched_total,
        "saved_total": saved_total,
        "sources": unique_sources,
        "failed_sources": failed_sources,
        "quality_skips_total": quality_skips_total,
        "errors": errors,
    }


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
    if src == "google_maps":
        return [f"https://www.google.com/maps/search/{q}"]
    if src == "indiamart":
        return [f"https://dir.indiamart.com/search.mp?ss={q}"]
    if src == "justdial":
        return [f"https://www.justdial.com/search?query={q}"]
    if src == "eworldtrade":
        return [f"https://www.eworldtrade.com/search?q={q}"]
    if src == "global_sources":
        return [f"https://www.globalsources.com/search?query={q}"]
    if src == "thomasnet":
        return [f"https://www.thomasnet.com/search.html?what={q}"]
    if src == "yelp":
        return [f"https://www.yelp.com/search?find_desc={q}"]
    if src == "faire":
        return [f"https://www.faire.com/search?q={q}"]
    registry_entry = runtime_settings.get_source_registry_entry(src)
    input_type = str((registry_entry or {}).get("input_type") or "").strip().lower()
    if registry_entry is not None and input_type == "keyword":
        return [f"https://www.google.com/search?q={q}+company+official+site"]
    return []
