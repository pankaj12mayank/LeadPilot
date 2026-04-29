from __future__ import annotations

from unittest.mock import patch

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
    assert "weighted_components" in str(out_sig.get("explanation") or "") or "weighted_components" in str(out_sig.get("reason") or "")


def test_score_lead_uses_admin_ai_weight_and_ai_score() -> None:
    lead = {
        "full_name": "Sam",
        "title": "Founder",
        "company_name": "Nova",
        "company_size": "11-50",
        "company_website": "https://nova.dev",
        "email": "sam@nova.dev",
        "source_platform": "linkedin",
        "ai_score": 90,
    }
    with patch(
        "backend.services.scoring_engine_service.runtime_settings.get_admin_config",
        return_value={
            "scoring_weights": {"role_weight": 10, "signal_weight": 10, "data_weight": 10},
            "scoring_control": {"ai_score": 70},
        },
    ):
        high = score_lead(lead)
    with patch(
        "backend.services.scoring_engine_service.runtime_settings.get_admin_config",
        return_value={
            "scoring_weights": {"role_weight": 30, "signal_weight": 30, "data_weight": 30},
            "scoring_control": {"ai_score": 10},
        },
    ):
        low = score_lead(lead)
    assert float(high["score"]) > float(low["score"])
