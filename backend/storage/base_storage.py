from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseStorage(ABC):
    """Storage backend contract (CSV, SQLite, Postgres)."""

    @abstractmethod
    def init_storage(self) -> None:
        ...

    @abstractmethod
    def create_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a new lead; returns the stored row including lead_id and timestamps."""
        ...

    @abstractmethod
    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def list_leads(self) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def update_lead(self, lead_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def delete_lead(self, lead_id: str) -> bool:
        ...

    @abstractmethod
    def update_status(self, lead_id: str, status: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def sync_leads(self, leads: List[Dict[str, Any]]) -> None:
        """Replace dataset with the given list (preserves legacy bulk CSV updates)."""
        ...
