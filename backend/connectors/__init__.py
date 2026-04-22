"""External connectors and platform definitions."""

from backend.connectors.capture_router import parse_lead_from_snapshot
from backend.connectors.platforms import PLATFORM_ALIASES, PLATFORM_CANONICAL

__all__ = [
    "PLATFORM_ALIASES",
    "PLATFORM_CANONICAL",
    "parse_lead_from_snapshot",
]
