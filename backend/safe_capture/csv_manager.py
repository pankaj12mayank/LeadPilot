"""
Legacy CSV entry points. Delegates to the storage factory so STORAGE_MODE
(csv | sqlite | postgres) is respected without breaking older imports.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.settings.lead_schema import LEAD_COLUMNS
from backend.storage.storage_factory import get_storage

# Backward-compatible name for older code / docs
COLUMNS = LEAD_COLUMNS


def init_csv() -> None:
    get_storage().init_storage()


def save_lead(lead_dict: Dict[str, Any]) -> None:
    get_storage().create_lead(lead_dict)


def read_leads() -> List[Dict[str, Any]]:
    return get_storage().list_leads()


def update_leads(leads_list: List[Dict[str, Any]]) -> None:
    get_storage().sync_leads(leads_list)
