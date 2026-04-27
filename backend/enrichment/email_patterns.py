"""Derive a public email domain and common pattern guesses (no verification)."""

from __future__ import annotations

import re
from typing import List
from urllib.parse import urlparse

_FREE = frozenset(
    {
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "icloud.com",
        "protonmail.com",
        "proton.me",
    }
)


def _domain_from_website(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = "https://" + u.lstrip("/")
    try:
        p = urlparse(u)
    except Exception:
        return ""
    host = (p.netloc or "").lower().split("@")[-1]
    if not host:
        return ""
    if host.startswith("www."):
        host = host[4:]
    if "." not in host:
        return ""
    if host in _FREE or any(host.endswith(f".{d}") for d in _FREE):
        return ""
    return host


def _split_name(full: str) -> tuple[str, str]:
    s = re.sub(r"\s+", " ", (full or "").strip())
    if not s:
        return "", ""
    parts = [p for p in s.replace("·", " ").split(" ") if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return re.sub(r"[^a-z0-9]", "", parts[0].lower())[:64], ""
    first = re.sub(r"[^a-z0-9]", "", parts[0].lower())[:64]
    last = re.sub(r"[^a-z0-9]", "", parts[-1].lower())[:64]
    return first, last


def email_candidates_from_name_and_url(
    full_name: str,
    company_website: str,
    *,
    max_n: int = 6,
) -> List[str]:
    """
    Patterns (as required): firstname@, firstname.lastname@, f.lastname@  (+ optional initials).

    Domain: taken from the company website host (skips public mail providers).
    """
    domain = _domain_from_website(company_website)
    if not domain:
        return []
    first, last = _split_name(full_name)
    if not first:
        return []

    out: list[str] = [f"{first}@{domain}"]
    if last:
        out.append(f"{first}.{last}@{domain}")
        c0 = first[0] if first else ""
        if c0:
            out.append(f"{c0}.{last}@{domain}")
    seen: set[str] = set()
    res: list[str] = []
    for e in out:
        e2 = e.lower()
        if e2 not in seen and len(seen) < max_n:
            seen.add(e2)
            res.append(e2)
    return res
