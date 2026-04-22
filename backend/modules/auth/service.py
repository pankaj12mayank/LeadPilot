from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services import auth_service


def register_user(email: str, password: str) -> Dict[str, Any]:
    return auth_service.create_user(email, password)


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    return auth_service.authenticate(email, password)
