"""Canonical lead lifecycle statuses (slug form)."""

from __future__ import annotations

from typing import FrozenSet

# Product statuses (Prompt 9)
ALLOWED_STATUSES: FrozenSet[str] = frozenset(
    {
        "new",
        "contacted",
        "replied",
        "follow_up_sent",
        "meeting_scheduled",
        "deal_discussion",
        "closed",
        "rejected",
    }
)

# Older records may still carry these; accepted on read / PATCH.
LEGACY_STATUSES: FrozenSet[str] = frozenset({"ready", "converted"})


def normalize_status(value: str | None) -> str:
    s = (value or "new").strip().lower().replace(" ", "_").replace("-", "_")
    if not s:
        return "new"
    if s in ALLOWED_STATUSES or s in LEGACY_STATUSES:
        return s
    return "new"


def assert_status_writable(value: str) -> str:
    """Raise ValueError if status cannot be persisted."""
    s = normalize_status(value)
    if s not in ALLOWED_STATUSES and s not in LEGACY_STATUSES:
        raise ValueError(
            f"Invalid status {value!r}. Expected one of: {', '.join(sorted(ALLOWED_STATUSES))} "
            f"(legacy: {', '.join(sorted(LEGACY_STATUSES))})"
        )
    return s


def display_label(slug: str) -> str:
    labels = {
        "new": "New",
        "contacted": "Contacted",
        "replied": "Replied",
        "follow_up_sent": "Follow-up Sent",
        "meeting_scheduled": "Meeting Scheduled",
        "deal_discussion": "Deal Discussion",
        "closed": "Closed",
        "rejected": "Rejected",
        "ready": "Follow-up Sent (legacy)",
        "converted": "Closed (legacy)",
    }
    return labels.get(slug, slug.replace("_", " ").title())
