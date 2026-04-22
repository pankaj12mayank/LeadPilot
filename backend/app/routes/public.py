from __future__ import annotations

from fastapi import APIRouter

from backend.services import runtime_settings

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/branding")
def public_branding() -> dict:
    """Unauthenticated branding for SPA shell (product name, logo, favicon)."""
    return runtime_settings.get_branding()
