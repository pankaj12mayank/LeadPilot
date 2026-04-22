"""Crunchbase: lightweight extraction from a DOM snapshot."""

from __future__ import annotations

import re
from typing import Any


def parse_crunchbase_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    url = str(snap.get("url") or "")
    h1 = str(snap.get("h1") or "").strip()
    doc_title = str(snap.get("title") or "").strip()
    text_sample = str(snap.get("textSample") or "")

    name = h1
    if not name and doc_title:
        name = re.split(r"\s*[-—|]\s*", doc_title, maxsplit=1)[0].strip()

    industry = ""
    m = re.search(r"(?im)\bindustry\b[:\s]+([^\n]+)", text_sample)
    if m:
        industry = m.group(1).strip()[:200]

    location = ""
    m2 = re.search(r"(?im)\blocation\b[:\s]+([^\n]+)", text_sample)
    if m2:
        location = m2.group(1).strip()[:200]

    website = ""
    wm = re.search(r"https?://[^\s)]+", text_sample)
    if wm:
        website = wm.group(0).strip().rstrip(".,);")

    email = ""
    em = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text_sample, flags=re.I)
    if em:
        email = em.group(0)

    return {
        "name": name,
        "title": "",
        "company": name,
        "industry": industry,
        "location": location,
        "website": website,
        "email": email,
        "profile_url": url,
    }
