from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.api.deps import get_current_admin
from backend.services import landing_config_service, settings_service

router = APIRouter(prefix="/admin/landing", tags=["admin-landing"])


class LandingConfigPatchBody(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class LandingGenerateBody(BaseModel):
    location: str = ""
    keyword_focus: str = ""


@router.get("/config")
def get_landing_config(_admin: dict = Depends(get_current_admin)) -> dict[str, Any]:
    return {"config": landing_config_service.get_landing_config()}


@router.patch("/config")
def patch_landing_config(body: LandingConfigPatchBody, _admin: dict = Depends(get_current_admin)) -> dict[str, Any]:
    saved = landing_config_service.save_landing_config(body.config or {})
    settings_service.emit_config_updated_event(["landing_config"])
    return {"ok": True, "config": saved}


@router.post("/generate-content")
def generate_landing_content(body: LandingGenerateBody, _admin: dict = Depends(get_current_admin)) -> dict[str, Any]:
    generated = landing_config_service.generate_ai_content(location=body.location, keyword_focus=body.keyword_focus)
    return {"ok": True, "generated": generated}
