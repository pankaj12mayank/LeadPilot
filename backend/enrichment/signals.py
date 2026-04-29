"""Map website + lead text into business signals (scaling, hiring, content gap, ads gap)."""

from __future__ import annotations

import re
from typing import Any, Dict

from backend.services import runtime_settings

from .website import WebsiteEnrichmentResult

# Growth / scale language (also used when site fetch failed but LinkedIn fields exist)
_SCALING_RE = re.compile(
    r"\b("
    r"scaling|scale-up|growing|growth|expanding|expansion|series [a-z0-9]+|"
    r"raised|funding|momentum|rapid|doubled|2x|3x|yoy|revenue"
    r")\b",
    re.I,
)


def _blob(lead: Dict[str, Any], site_text: str) -> str:
    parts = [
        str(lead.get("title") or ""),
        str(lead.get("full_name") or lead.get("name") or ""),
        str(lead.get("company_name") or lead.get("company") or ""),
        str(lead.get("industry") or ""),
        str(lead.get("notes") or ""),
        str(lead.get("location") or ""),
        site_text or "",
    ]
    return " ".join(p for p in parts if p).lower()


def build_signals(ws: WebsiteEnrichmentResult, lead: Dict[str, Any]) -> Dict[str, bool]:
    """
    Return keys: scaling, hiring, content_gap, ads_gap (all bool).

    - *content_gap* = no clear blog / resources trail on the crawl (heuristic).
    - *ads_gap* = no obvious paid/performance marketing signals in HTML.
    """
    text = (ws.text_sample or "") if ws and ws.ok else ""
    b = _blob(lead, text)
    cfg = runtime_settings.get_admin_config()
    sig_cfg = cfg.get("signals_config") or {}

    scaling = bool(_SCALING_RE.search(b))

    hiring = bool(ws and ws.ok and ws.is_hiring)
    if not hiring:
        hiring = bool(re.search(r"\b(hiring|we are hiring|join our team|open roles)\b", b))

    content_gap = not (ws and ws.ok and ws.has_blog)
    ads_gap = not (ws and ws.ok and ws.ads_presence)

    if not bool(sig_cfg.get("hiring_enabled", True)):
        hiring = False
    if not bool(sig_cfg.get("scaling_enabled", True)):
        scaling = False

    return {
        "scaling": scaling,
        "hiring": hiring,
        "content_gap": content_gap,
        "ads_gap": ads_gap,
    }
