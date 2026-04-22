from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.settings.lead_schema import normalize_lead_row, row_for_write
from backend.storage.storage_factory import get_storage


def init_storage() -> None:
    get_storage().init_storage()


def create_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    return get_storage().create_lead(row_for_write(lead))


def get_lead(lead_id: str) -> Optional[Dict[str, Any]]:
    return get_storage().get_lead(lead_id)


def list_leads() -> List[Dict[str, Any]]:
    return get_storage().list_leads()


def update_lead(lead_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_storage().update_lead(lead_id, patch)


def delete_lead(lead_id: str) -> bool:
    return get_storage().delete_lead(lead_id)


def update_status(lead_id: str, status: str) -> Optional[Dict[str, Any]]:
    return get_storage().update_status(lead_id, status)


def sync_leads(leads: List[Dict[str, Any]]) -> None:
    get_storage().sync_leads([normalize_lead_row(x) for x in leads])
