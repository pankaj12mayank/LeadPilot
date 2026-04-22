"""Validate lead input before scoring or persistence."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def validate_lead(lead: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    name = str(lead.get("name") or "").strip()
    platform = str(lead.get("platform") or "").strip()
    profile_url = str(lead.get("profile_url") or "").strip()

    if not name:
        errors.append("name is required")
    if len(name) > 200:
        errors.append("name is too long (max 200 characters)")

    if not platform:
        errors.append("platform is required")

    if not profile_url:
        errors.append("profile_url is required")
    elif not (profile_url.startswith("http://") or profile_url.startswith("https://")):
        errors.append("profile_url should start with http:// or https://")

    email = str(lead.get("email") or "").strip()
    if email and not _simple_email_ok(email):
        errors.append("email format looks invalid")

    phone = str(lead.get("phone") or "").strip()
    if phone and len(phone) > 40:
        errors.append("phone is too long")

    return len(errors) == 0, errors


def _simple_email_ok(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def sanitize_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Strip string fields in place (mutates copy-safe via new dict)."""
    out = dict(lead)
    for k, v in list(out.items()):
        if isinstance(v, str):
            out[k] = v.strip()
    return out
