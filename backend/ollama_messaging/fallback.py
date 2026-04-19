from __future__ import annotations

import textwrap
from typing import Any, Dict

from backend.ollama_messaging.types import LeadMessageInput, LeadMessageOutput


def _clean(s: Any) -> str:
    return str(s or "").strip()


def build_fallback_pack(lead: LeadMessageInput) -> LeadMessageOutput:
    """Deterministic templates when Ollama is unavailable or returns invalid output."""
    name = _clean(lead.get("name")) or "there"
    company = _clean(lead.get("company"))
    industry = _clean(lead.get("industry"))
    title = _clean(lead.get("job_title"))
    site = _clean(lead.get("company_website"))
    pains = _clean(lead.get("pain_points"))
    opp = _clean(lead.get("opportunity_summary"))

    if title and company:
        who_line = f"{name}, {title} at {company}"
    elif company:
        who_line = f"{name} at {company}"
    else:
        who_line = name

    site_hint = f" ({site})" if site else ""
    ind_line = f" in {industry}" if industry else ""

    short_summary = textwrap.dedent(
        f"""
        {company or "This organization"}{ind_line} may be evaluating ways to reduce friction in
        day-to-day operations and growth. {opp or "A focused conversation could clarify fit and next steps."}
        """
    ).strip()

    if pains:
        pain_block = "\n".join(f"- {ln.strip()}" for ln in pains.splitlines() if ln.strip())
        if not pain_block.startswith("-"):
            pain_block = "\n".join(f"- {p.strip()}" for p in pains.replace(";", ",").split(",") if p.strip())
    else:
        pain_block = (
            "- Scaling process and tooling without adding heavy overhead\n"
            "- Keeping teams aligned as priorities shift"
        )

    linkedin_message = textwrap.dedent(
        f"""
        Hi {name},

        I noticed your work{(" at " + company) if company else ""}{(" as " + title) if title else ""}.
        {("Re: " + pains[:200] + " — ") if pains else ""}We're exploring whether {opp[:180] if opp else "our approach"} could be relevant without adding noise to your week.

        Open to a brief exchange if useful — happy to work around your schedule.

        Best
        """
    ).strip()

    pain_intro = ("Context I have: " + pains[:280] + "\n\n") if pains else ""

    email_message = textwrap.dedent(
        f"""
        Hi {who_line},

        I came across {company or "your team"}{site_hint} and wanted to reach out personally.
        {pain_intro}{opp or "I'd value a short conversation to see if there's a fit."}

        If this isn't a priority right now, no problem — a one-line reply helps either way.

        Thanks,
        """
    ).strip()

    followup_message = textwrap.dedent(
        f"""
        Hi {name},

        Following up lightly — I know inboxes are busy.
        {("Still thinking about " + pains[:160] + " — ") if pains else ""}{opp[:200] if opp else "Happy to share a concise overview or pause if timing isn't right."}

        Best,
        """
    ).strip()

    out: LeadMessageOutput = {
        "linkedin_message": " ".join(linkedin_message.split()),
        "email_message": email_message.strip(),
        "followup_message": followup_message.strip(),
        "short_summary": " ".join(short_summary.split()),
        "pain_points": pain_block.strip(),
    }
    return out


def merge_with_fallback(partial: Dict[str, Any], lead: LeadMessageInput) -> LeadMessageOutput:
    fb = build_fallback_pack(lead)

    def pick(key: str) -> str:
        v = partial.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
        return fb[key]  # type: ignore[literal-required]

    return {
        "linkedin_message": pick("linkedin_message"),
        "email_message": pick("email_message"),
        "followup_message": pick("followup_message"),
        "short_summary": pick("short_summary"),
        "pain_points": pick("pain_points"),
    }
