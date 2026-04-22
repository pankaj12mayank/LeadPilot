"""Unit tests for safe capture scoring (no Playwright)."""

from __future__ import annotations

from backend.safe_capture.capture_score import score_lead


def test_score_founder_saas_company_website_startup_hot_tier() -> None:
    lead = {
        "name": "Jane Doe",
        "title": "Founder & CEO",
        "company": "Acme SaaS",
        "industry": "SaaS",
        "location": "",
        "website": "https://acme.example",
        "email": "",
        "source_platform": "linkedin",
        "profile_url": "https://linkedin.com/in/jane",
        "score": 0,
        "tier": "COLD",
        "status": "NEW",
    }
    meta = {"startup_early_signal": True}
    score, tier = score_lead(lead, meta)
    assert score == 85
    assert tier == "HOT"


def test_score_minimal_cold() -> None:
    lead = {
        "name": "",
        "title": "Analyst",
        "company": "",
        "industry": "",
        "location": "",
        "website": "",
        "email": "",
        "source_platform": "generic",
        "profile_url": "https://example.com/p",
        "score": 0,
        "tier": "COLD",
        "status": "NEW",
    }
    score, tier = score_lead(lead, {})
    assert score == 0
    assert tier == "COLD"


def test_score_warm_band() -> None:
    lead = {
        "name": "Pat",
        "title": "Head of Marketing",
        "company": "Contoso",
        "industry": "Marketing",
        "location": "",
        "website": "",
        "email": "",
        "source_platform": "apollo",
        "profile_url": "https://apollo.io/#/people/x",
        "score": 0,
        "tier": "COLD",
        "status": "NEW",
    }
    score, tier = score_lead(lead, {})
    assert score == 35
    assert tier == "COLD"

    lead2 = dict(lead)
    lead2["website"] = "https://contoso.com"
    score2, tier2 = score_lead(lead2, {})
    assert score2 == 45
    assert tier2 == "WARM"
