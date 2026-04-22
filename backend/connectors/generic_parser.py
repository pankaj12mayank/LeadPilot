"""Generic company / personal sites from a DOM snapshot."""

from __future__ import annotations

import re
from typing import Any


def parse_generic_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    url = str(snap.get("url") or "")
    h1 = str(snap.get("h1") or "").strip()
    doc_title = str(snap.get("title") or "").strip()
    og = snap.get("og") or {}
    og_title = str(og.get("title") or "").strip()
    text_sample = str(snap.get("textSample") or "")

    name = h1 or re.split(r"\s*[-—|]\s*", og_title or doc_title, maxsplit=1)[0].strip()

    website = ""
    cand = og.get("url")
    if isinstance(cand, str) and cand.startswith("http"):
        website = cand.strip()
    if not website:
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
        "industry": "",
        "location": "",
        "website": website,
        "email": email,
        "profile_url": url,
    }
