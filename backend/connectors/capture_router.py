"""Route a DOM snapshot to the correct source-specific parser."""

from __future__ import annotations

from typing import Any

from backend.connectors.apollo_parser import parse_apollo_snapshot
from backend.connectors.clutch_parser import parse_clutch_snapshot
from backend.connectors.crunchbase_parser import parse_crunchbase_snapshot
from backend.connectors.generic_parser import parse_generic_snapshot
from backend.connectors.linkedin_parser import parse_linkedin_snapshot


def parse_lead_from_snapshot(platform: str, snap: dict[str, Any]) -> dict[str, Any]:
    """
    Parse visible lead fields for a detected ``platform`` slug.

    Returns a flat dict of raw string fields (may contain empty strings).
    """
    slug = (platform or "generic").strip().lower()
    if slug == "linkedin":
        return parse_linkedin_snapshot(snap)
    if slug == "apollo":
        return parse_apollo_snapshot(snap)
    if slug == "crunchbase":
        return parse_crunchbase_snapshot(snap)
    if slug == "clutch":
        return parse_clutch_snapshot(snap)
    return parse_generic_snapshot(snap)
