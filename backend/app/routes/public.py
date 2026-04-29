from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services import landing_config_service, runtime_settings
from backend.utils.logger import get_logger

router = APIRouter(prefix="/public", tags=["public"])
logger = get_logger(__name__)


class LandingTrackBody(BaseModel):
    event: str
    section: str = ""
    target: str = ""


@router.get("/branding")
def public_branding() -> dict:
    """Unauthenticated branding for SPA shell (product name, logo, favicon)."""
    return runtime_settings.get_branding()


@router.get("/landing-config")
def public_landing_config() -> dict:
    return {"config": landing_config_service.get_landing_config()}


@router.post("/landing-track")
def public_landing_track(body: LandingTrackBody) -> dict:
    logger.info(
        "landing_analytics event=%s section=%s target=%s",
        str(body.event or "").strip(),
        str(body.section or "").strip(),
        str(body.target or "").strip(),
    )
    return {"ok": True}
