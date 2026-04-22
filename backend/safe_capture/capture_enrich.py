"""Conservative enrichment from visible page text (no external APIs)."""

from __future__ import annotations

import re
from typing import Any

_INDUSTRY_RULES: tuple[tuple[str, str], ...] = (
    ("saas", "SaaS"),
    ("software as a service", "SaaS"),
    ("marketing", "Marketing"),
    ("growth marketing", "Marketing"),
    ("demand gen", "Marketing"),
    ("real estate", "Real Estate"),
    ("realtor", "Real Estate"),
    ("property", "Real Estate"),
)

_STARTUP_MARKERS: tuple[str, ...] = (
    "pre-seed",
    "pre seed",
    "seed round",
    "seed funding",
    "series a",
    "series-a",
    "early stage",
    "early-stage",
    "early stage startup",
    "early-stage startup",
    "startup",
)


def _combined_blob(lead: dict[str, Any], text_sample: str) -> str:
    parts = [
        str(lead.get("title") or ""),
        str(lead.get("company") or ""),
        str(lead.get("name") or ""),
        str(lead.get("industry") or ""),
        str(text_sample or ""),
    ]
    return " ".join(parts).lower()


def enrich_lead(lead: dict[str, Any], text_sample: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Return ``(enriched_lead, meta)`` where ``meta`` is JSON-serializable audit context.

    Rules are intentionally shallow: only fill missing industry when a keyword hits.
    """
    out = dict(lead)
    meta: dict[str, Any] = {}

    blob = _combined_blob(out, text_sample)
    if not str(out.get("industry") or "").strip():
        for needle, label in _INDUSTRY_RULES:
            if needle in blob:
                out["industry"] = label
                meta["industry_inferred"] = label
                break

    startup_hit = any(m in blob for m in _STARTUP_MARKERS)
    meta["startup_early_signal"] = bool(startup_hit)
    if startup_hit:
        meta.setdefault("signals", []).append("startup_stage_early")

    website = str(out.get("website") or "").strip()
    if website and not re.match(r"^https?://", website, flags=re.I):
        out["website"] = "https://" + website.lstrip("/")
        meta["website_normalized"] = True

    return out, meta
