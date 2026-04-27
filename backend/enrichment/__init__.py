"""On-site company enrichment (no paid APIs): fetch website, heuristics, signals, email patterns."""

from __future__ import annotations

from .email_patterns import email_candidates_from_name_and_url
from .signals import build_signals
from .website import WebsiteEnrichmentResult, fetch_website_enrichment

__all__ = [
    "WebsiteEnrichmentResult",
    "fetch_website_enrichment",
    "build_signals",
    "email_candidates_from_name_and_url",
]
