from __future__ import annotations

from typing import Any, Dict

from backend.services import settings_service


def load_app_settings() -> Dict[str, Any]:
    return settings_service.load_settings()


def save_app_settings_patch(patch: Dict[str, Any]) -> Dict[str, Any]:
    return settings_service.patch_settings(patch)
