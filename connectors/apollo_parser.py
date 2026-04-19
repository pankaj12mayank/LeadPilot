"""Apollo.io: best-effort parse from a DOM snapshot."""

from __future__ import annotations

import re
from typing import Any


def parse_apollo_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    url = str(snap.get("url") or "")
    h1 = str(snap.get("h1") or "").strip()
    doc_title = str(snap.get("title") or "").strip()
    text_sample = str(snap.get("textSample") or "")

    name = h1 or re.split(r"\s*[-—|]\s*", doc_title, maxsplit=1)[0].strip()

    title_guess = ""
    company_guess = ""
    for ln in [x.strip() for x in text_sample.splitlines() if x.strip()][:40]:
        if " at " in ln.lower() and len(ln) < 220:
            parts = re.split(r"\s+at\s+", ln, maxsplit=1, flags=re.I)
            title_guess = parts[0].strip()
            company_guess = parts[1].strip() if len(parts) > 1 else ""
            break

    email = ""
    em = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text_sample, flags=re.I)
    if em:
        email = em.group(0)

    website = ""
    wm = re.search(r"https?://[^\s)]+", text_sample)
    if wm:
        website = wm.group(0).strip().rstrip(".,);")

    return {
        "name": name,
        "title": title_guess,
        "company": company_guess,
        "industry": "",
        "location": "",
        "website": website,
        "email": email,
        "profile_url": url,
    }
