"""LinkedIn: extract visible profile signals from a DOM snapshot (manual flow)."""

from __future__ import annotations

import re
from typing import Any


def parse_linkedin_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    url = str(snap.get("url") or "")
    h1 = str(snap.get("h1") or "").strip()
    title = str(snap.get("title") or "").strip()
    og_title = str((snap.get("og") or {}).get("title") or "").strip()
    text_sample = str(snap.get("textSample") or "")

    def _split_title_bar(s: str) -> str:
        return re.split(r"\s*\|\s*", s, maxsplit=1)[0].strip()

    name = h1 or _split_title_bar(og_title) or _split_title_bar(title)
    headline = ""
    lines = [ln.strip() for ln in text_sample.splitlines() if ln.strip()]
    if name and lines:
        for i, ln in enumerate(lines[:8]):
            if ln == name and i + 1 < len(lines):
                headline = lines[i + 1]
                break
    if not headline and lines:
        for ln in lines[:6]:
            if ln != name and (" at " in ln.lower() or " | " in ln):
                headline = ln
                break

    title_part, company_part = "", ""
    if headline:
        lower = headline.lower()
        if " at " in lower:
            parts = re.split(r"\s+at\s+", headline, maxsplit=1, flags=re.I)
            title_part = parts[0].strip()
            company_part = parts[1].strip() if len(parts) > 1 else ""
        elif " | " in headline:
            parts = [p.strip() for p in headline.split("|", 1)]
            title_part = parts[0]
            company_part = parts[1] if len(parts) > 1 else ""

    location = ""
    for ln in lines[:25]:
        if re.search(r"\b(United States|India|UK|Canada|Germany|France|Australia)\b", ln):
            location = ln
            break

    website = ""
    m = re.search(r"https?://[^\s)]+", text_sample)
    if m:
        website = m.group(0).strip().rstrip(".,);")

    email = ""
    em = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text_sample, flags=re.I)
    if em:
        email = em.group(0)

    return {
        "name": name,
        "title": title_part or headline,
        "company": company_part,
        "industry": "",
        "location": location,
        "website": website,
        "email": email,
        "profile_url": url,
    }
