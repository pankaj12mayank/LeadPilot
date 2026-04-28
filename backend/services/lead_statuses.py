"""Canonical lead lifecycle statuses (slug form) — LinkedIn / CRM pipeline."""

from __future__ import annotations

from typing import FrozenSet

# Current product statuses (match lead capture + CRM pills)
ALLOWED_STATUSES: FrozenSet[str] = frozenset(
    {
        "new",
        "request_sent",
        "message_sent",
        "replied_got",
        "on_discussion",
        "interested",
        "deal",
        "close",
        "not_interested",
    }
)

# Old slugs (pre-migration rows in DB) → canonical
LEGACY_TO_CANON: dict[str, str] = {
    "contacted": "message_sent",
    "replied": "replied_got",
    "follow_up": "on_discussion",
    "follow_up_sent": "message_sent",
    "meeting_scheduled": "on_discussion",
    "deal_discussion": "deal",
    "closed": "close",
    "rejected": "not_interested",
    "ready": "message_sent",
    "converted": "close",
}

LEGACY_ALIASES: FrozenSet[str] = frozenset(LEGACY_TO_CANON.keys())


def _slug(value: str | None) -> str:
    s = (value or "new").strip().lower().replace(" ", "_").replace("-", "_")
    return s if s else "new"


def normalize_status(value: str | None) -> str:
    """Return canonical status for display/logic; unknown slugs default to **new**."""
    s = _slug(value)
    if s in ALLOWED_STATUSES:
        return s
    if s in LEGACY_TO_CANON:
        return LEGACY_TO_CANON[s]
    return "new"


def assert_status_writable(value: str) -> str:
    """Return canonical status for DB or raise if value is not allowed (including legacy aliases)."""
    s = _slug(value)
    if s in LEGACY_TO_CANON:
        return LEGACY_TO_CANON[s]
    if s in ALLOWED_STATUSES:
        return s
    raise ValueError(
        f"Invalid status {value!r}. Expected one of: {', '.join(sorted(ALLOWED_STATUSES))} "
        f"or legacy alias: {', '.join(sorted(LEGACY_ALIASES))}"
    )


def display_label(slug: str) -> str:
    labels: dict[str, str] = {
        "new": "New",
        "request_sent": "Request Sent",
        "message_sent": "Message Sent",
        "replied_got": "Replied got",
        "on_discussion": "On Discussion",
        "interested": "Interested",
        "deal": "Deal",
        "close": "Close",
        "not_interested": "Not interested",
        # legacy (display if raw still in DB)
        "contacted": "Message Sent",
        "replied": "Replied",
        "follow_up": "Follow-up",
        "follow_up_sent": "Message Sent",
        "meeting_scheduled": "On Discussion",
        "deal_discussion": "Deal",
        "closed": "Close",
        "rejected": "Not interested",
        "ready": "Message Sent",
        "converted": "Close",
    }
    k = (slug or "new").strip().lower().replace(" ", "_")
    if k in labels:
        return labels[k]
    return k.replace("_", " ").title()
