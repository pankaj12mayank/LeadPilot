from __future__ import annotations

from typing import Any

from backend.lead_scoring.tiers import assign_tier
from backend.services import runtime_settings


def _clamp(v: Any, low: float = 0.0, high: float = 100.0) -> float:
    try:
        x = float(v)
    except Exception:
        x = 0.0
    return max(low, min(high, x))


def get_scoring_weights() -> dict[str, float]:
    cfg = runtime_settings.get_admin_config()
    scoring = cfg.get("scoring_weights") or {}
    control = cfg.get("scoring_control") or {}
    role_w = max(1.0, float(scoring.get("role_weight") or control.get("role") or 40))
    signal_w = max(1.0, float(scoring.get("signal_weight") or control.get("signals") or 35))
    data_w = max(1.0, float(scoring.get("data_weight") or 25))
    ai_w = max(1.0, float(control.get("ai_score") or 25))
    return {
        "role_relevance": role_w,
        "signals": signal_w,
        "data_completeness": data_w,
        "ai_score": ai_w,
    }


def composite_score(
    *,
    role_relevance: float,
    signals: float,
    data_completeness: float,
    ai_score: float,
) -> dict[str, Any]:
    weights = get_scoring_weights()
    total_w = sum(float(v) for v in weights.values())
    final = (
        (_clamp(role_relevance) * weights["role_relevance"])
        + (_clamp(signals) * weights["signals"])
        + (_clamp(data_completeness) * weights["data_completeness"])
        + (_clamp(ai_score) * weights["ai_score"])
    ) / max(1.0, total_w)
    score = float(max(1.0, min(100.0, round(final, 2))))
    tier = assign_tier(score)
    return {
        "score": score,
        "tier": tier,
        "weights": weights,
        "inputs": {
            "role_relevance": _clamp(role_relevance),
            "signals": _clamp(signals),
            "data_completeness": _clamp(data_completeness),
            "ai_score": _clamp(ai_score),
        },
    }
