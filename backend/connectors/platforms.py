"""Supported lead source platforms (normalized identifiers)."""

from __future__ import annotations

from typing import FrozenSet

PLATFORM_CANONICAL: FrozenSet[str] = frozenset(
    {
        "linkedin",
        "apollo",
        "upwork",
        "fiverr",
        "clutch",
        "crunchbase",
        "wellfound",
        "google_maps",
        "justdial",
    }
)

# Human labels -> canonical slug
PLATFORM_ALIASES: dict[str, str] = {
    "linkedin": "linkedin",
    "apollo": "apollo",
    "upwork": "upwork",
    "fiverr": "fiverr",
    "clutch": "clutch",
    "crunchbase": "crunchbase",
    "wellfound": "wellfound",
    "angel list": "wellfound",
    "angellist": "wellfound",
    "google maps": "google_maps",
    "google_maps": "google_maps",
    "gmaps": "google_maps",
    "justdial": "justdial",
    "just dial": "justdial",
    "other": "other",
}
