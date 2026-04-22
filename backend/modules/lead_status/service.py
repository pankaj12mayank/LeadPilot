from __future__ import annotations

from typing import Any, Dict, List

from backend.services import status_history_service


def record_status_change(lead_id: str, old_status: str, new_status: str) -> None:
    status_history_service.record_change(lead_id, old_status, new_status)


def list_status_history(lead_id: str) -> List[Dict[str, Any]]:
    return status_history_service.list_for_lead(lead_id)
