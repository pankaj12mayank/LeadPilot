"""Unit tests for on-site enrichment (no network)."""

from __future__ import annotations

from backend.enrichment.email_patterns import email_candidates_from_name_and_url
from backend.enrichment.signals import build_signals
from backend.enrichment.website import WebsiteEnrichmentResult
from backend.lead_scoring.enrichment_scoring import score_lead_enriched


def test_email_candidates_basic() -> None:
    c = email_candidates_from_name_and_url("John Doe", "https://acme.com/about")
    assert f"john@acme.com" in c
    assert f"john.doe@acme.com" in c
    assert f"j.doe@acme.com" in c


def test_signals_from_website_and_lead() -> None:
    ws = WebsiteEnrichmentResult(ok=True, has_blog=True, is_hiring=True, ads_presence=True, text_sample="we are hiring")
    lead = {"title": "CEO", "company_name": "Co", "full_name": "A B", "industry": "SaaS"}
    s = build_signals(ws, lead)
    assert s["hiring"] is True
    assert s["content_gap"] is False
    assert s["ads_gap"] is False


def test_enriched_score_range() -> None:
    lead = {
        "full_name": "Jane Smith",
        "title": "Chief Executive Officer",
        "company_name": "Acme",
        "company_size": "51-200",
        "linkedin_url": "https://linkedin.com/in/x",
        "company_website": "https://acme.com",
        "email": "j@acme.com",
    }
    sig = {
        "scaling": True,
        "hiring": True,
        "content_gap": True,
        "ads_gap": True,
    }
    out = score_lead_enriched(lead, signals=sig, pain_points="- a\n- b\n- c", website_fetch_ok=True)
    assert 1 <= float(out["score"]) <= 100
    assert out["tier"] in ("hot", "warm", "cold")
    assert "breakdown" in out
