from __future__ import annotations

from typing import Any, Dict

from backend.services import analytics_service


def dashboard_snapshot() -> Dict[str, Any]:
    return analytics_service.dashboard()
