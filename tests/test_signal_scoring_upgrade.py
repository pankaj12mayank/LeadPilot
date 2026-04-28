from __future__ import annotations

from backend.lead_scoring.engine import score_lead


def test_score_lead_extended_with_signals() -> None:
    base = {
        "full_name": "Jane Doe",
        "title": "VP Marketing",
        "company_name": "Acme",
        "company_size": "51-200",
        "company_website": "https://acme.com",
        "email": "jane@acme.com",
        "source_platform": "linkedin",
        "location": "US",
    }
    out_plain = score_lead(dict(base))
    out_sig = score_lead(
        {
            **base,
            "signal_hiring": 1,
            "signal_scaling": 1,
            "signal_content_gap": 1,
            "signal_ads_gap": 1,
        }
    )
    assert float(out_sig["score"]) >= float(out_plain["score"])
    assert "signal_extension" in str(out_sig.get("explanation") or "") or "Signals +" in str(out_sig.get("reason") or "")
