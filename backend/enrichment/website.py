"""Open company website, extract text and cheap HTML heuristics (blog, hiring, marketing/ads)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

# Keep reads small; real sites can be huge.
_MAX_BYTES = 1_500_000
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Paths / substrings for hiring
_HIRING_PATH_RE = re.compile(
    r"(/careers|/jobs|/work-with-us|/join|/team|/opportunities|/vacancies|hiring)(/|$|\.|\?)",
    re.I,
)
_HIRING_VENDORS = re.compile(
    r"(lever\.co|greenhouse\.io|i\.smartrecruiters|workable\.|ashbyhq\.com|bamboohr|jobvite)",
    re.I,
)

# Blog / content hubs
_BLOG_RE = re.compile(
    r"(/blog|/blogs|/insights|/resources|/articles|/news(?!letter))(/|$|\?)", re.I
)

# "Ads" / performance marketing (pixels, ad platforms, or explicit copy)
_ADS_RE = re.compile(
    r"(gtag\(|fbq\(|fbevents|googleads|googlesyndication|doubleclick|adwords|facebook\.com/tr|"
    r"linkedin\.com/px|microsoft\.com/clarity|marketo|pardot|hubspot.*tracking|"
    r"\bPPC\b|\bSEM\b|paid search|google ads|facebook ads|performance marketing)",
    re.I,
)

_WS_SPLIT = re.compile(r"\s+")


@dataclass
class WebsiteEnrichmentResult:
    url: str = ""
    final_url: str = ""
    ok: bool = False
    has_blog: bool = False
    is_hiring: bool = False
    ads_presence: bool = False
    text_sample: str = ""
    error: str = ""
    http_status: int = 0
    # Raw signals for JSON export (all JSON-serializable)
    details: dict[str, Any] = field(default_factory=dict)


def _normalize_url(raw: str) -> str:
    s = (raw or "").strip()
    if not s or s.lower() in ("none", "nan", "n/a"):
        return ""
    if not s.startswith(("http://", "https://")):
        s = "https://" + s.lstrip("/")
    try:
        p = urlparse(s)
    except Exception:
        return ""
    if p.scheme not in ("http", "https") or not p.netloc:
        return ""
    return s


def _visible_text(soup: Any) -> str:
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()
    t = soup.get_text(separator=" ", strip=True)
    t = _WS_SPLIT.sub(" ", t)
    return t[:120_000]


def fetch_website_enrichment(url: str, *, timeout: float = 16.0) -> WebsiteEnrichmentResult:
    """
    GET the page (first hop), parse with BeautifulSoup, and fill booleans + text sample.
    Never raises: failed HTTP/HTML still returns a result with ``ok`` False.
    """
    norm = _normalize_url(url)
    out = WebsiteEnrichmentResult(url=norm, final_url=norm)
    if not norm:
        out.error = "empty_url"
        return out

    try:
        import httpx
    except ImportError as e:  # pragma: no cover
        out.error = f"httpx_missing: {e}"
        return out

    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"},
        ) as client:
            r = client.get(norm)
            out.http_status = int(r.status_code)
            r.raise_for_status()
            if r.text is None:  # pragma: no cover
                out.error = "empty_response"
                return out
            raw_html = (r.text or "")[:_MAX_BYTES]
            if hasattr(r, "url"):
                out.final_url = str(getattr(r, "url", "") or norm)[:2048]
    except Exception as e:  # noqa: BLE001
        out.error = f"http_error: {e!s}"[:500]
        return out

    try:
        from bs4 import BeautifulSoup
    except ImportError as e:  # pragma: no cover
        out.error = f"bs4_missing: {e!s}"
        return out

    try:
        soup = BeautifulSoup(raw_html, "lxml")
    except Exception:
        try:
            soup = BeautifulSoup(raw_html, "html.parser")
        except Exception as e:  # noqa: BLE001
            out.error = f"parse_error: {e!s}"[:500]
            return out

    # Resolve links in page for /careers, /blog on same host
    base = out.final_url or norm
    blog_hit = _BLOG_RE.search(raw_html) is not None
    if not blog_hit and soup:
        for a in soup.find_all("a", href=True)[:500]:
            href = str(a.get("href", "") or "").strip()
            full = urljoin(base, href)
            if _BLOG_RE.search(full) or _BLOG_RE.search(href):
                blog_hit = True
                break
    hire_hit = _HIRING_PATH_RE.search(raw_html) is not None
    if not hire_hit and soup:
        for a in soup.find_all("a", href=True)[:600]:
            h = (a.get("href") or "") + " " + (a.get("title") or "")
            if _HIRING_VENDORS.search(h) or "hiring" in h.lower() or "career" in h.lower():
                hire_hit = True
                break
    if not hire_hit:
        hire_hit = _HIRING_VENDORS.search(raw_html) is not None

    ads_hit = _ADS_RE.search(raw_html) is not None
    if not ads_hit and soup:
        for meta in soup.find_all("meta", limit=80):
            c = str(meta.get("content") or "")
            if c and _ADS_RE.search(c):
                ads_hit = True
                break

    text = _visible_text(soup) if soup else ""
    if not text:
        text = _WS_SPLIT.sub(" ", re.sub(r"<[^>]+>", " ", raw_html)[:200_000])

    out.ok = True
    out.has_blog = bool(blog_hit)
    out.is_hiring = bool(hire_hit)
    out.ads_presence = bool(ads_hit)
    out.text_sample = (text or "")[:8000]
    out.details = {
        "http_status": out.http_status,
        "final_url": (out.final_url or norm)[:2000],
        "has_blog": out.has_blog,
        "is_hiring": out.is_hiring,
        "ads_presence": out.ads_presence,
    }
    return out
