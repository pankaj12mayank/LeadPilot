from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.deps import get_current_user
from backend.app.schemas.platform import (
    PlatformBuiltinPatch,
    PlatformCreate,
    PlatformResponse,
    PlatformUpdate,
)
from backend.scraper.session_manager import SessionManager
from backend.scraper.urls import LOGIN_START_URLS, login_url
from backend.connectors.platforms import PLATFORM_CANONICAL
from backend.services import platform_registry_service

router = APIRouter(prefix="/platforms", tags=["platforms"])


def _enrich(slug: str, row: PlatformResponse) -> PlatformResponse:
    sm = SessionManager()
    return row.model_copy(
        update={
            "session_profile": sm.has_session(slug),
            "session_connected": sm.session_connected(slug),
        }
    )


def _builtin_items() -> List[PlatformResponse]:
    out: List[PlatformResponse] = []
    for slug in sorted(PLATFORM_CANONICAL | {"other"}):
        active = platform_registry_service.get_builtin_active(slug)
        label = slug.replace("_", " ").title()
        lu = login_url(slug) if slug in LOGIN_START_URLS else None
        base = PlatformResponse(
            platform_id=None,
            slug=slug,
            label=label,
            active=active,
            builtin=True,
            created_at=None,
            login_url=lu,
        )
        out.append(_enrich(slug, base))
    return out


@router.get("/", response_model=List[PlatformResponse])
def list_platforms(_user: dict = Depends(get_current_user)) -> List[PlatformResponse]:
    items = _builtin_items()
    for row in platform_registry_service.list_custom():
        slug = str(row["slug"])
        base = PlatformResponse(
            platform_id=row["platform_id"],
            slug=slug,
            label=row["label"],
            active=row["active"],
            builtin=False,
            created_at=row["created_at"],
            login_url=(row.get("login_url") or "") or None,
        )
        items.append(_enrich(slug, base))
    return items


@router.post("/", response_model=PlatformResponse)
def create_platform(
    body: PlatformCreate, _user: dict = Depends(get_current_user)
) -> PlatformResponse:
    try:
        row = platform_registry_service.create_platform(body.slug, body.label, body.login_url)
    except ValueError as e:
        msg = str(e)
        if msg == "reserved_slug":
            raise HTTPException(status_code=400, detail="Slug is reserved for built-in platforms")
        if msg == "slug_taken":
            raise HTTPException(status_code=400, detail="Slug already exists")
        if msg == "login_url_required":
            raise HTTPException(status_code=400, detail="Login URL is required for custom platforms")
        raise HTTPException(status_code=400, detail="Could not create platform")
    slug = str(row["slug"])
    base = PlatformResponse(
        platform_id=row["platform_id"],
        slug=slug,
        label=row["label"],
        active=row["active"],
        builtin=False,
        created_at=row["created_at"],
        login_url=row.get("login_url") or body.login_url,
    )
    return _enrich(slug, base)


@router.patch("/builtin/{slug}", response_model=PlatformResponse)
def patch_builtin_platform(
    slug: str,
    body: PlatformBuiltinPatch,
    _user: dict = Depends(get_current_user),
) -> PlatformResponse:
    s = slug.strip().lower().replace(" ", "_")
    if s not in PLATFORM_CANONICAL and s != "other":
        raise HTTPException(status_code=404, detail="Unknown built-in platform")
    platform_registry_service.set_builtin_active(s, body.active)
    label = s.replace("_", " ").title()
    lu = login_url(s) if s in LOGIN_START_URLS else None
    base = PlatformResponse(
        platform_id=None,
        slug=s,
        label=label,
        active=body.active,
        builtin=True,
        created_at=None,
        login_url=lu,
    )
    return _enrich(s, base)


@router.patch("/{platform_id}", response_model=PlatformResponse)
def update_platform(
    platform_id: int,
    body: PlatformUpdate,
    _user: dict = Depends(get_current_user),
) -> PlatformResponse:
    row = platform_registry_service.update_platform(
        platform_id, label=body.label, active=body.active
    )
    if not row:
        raise HTTPException(status_code=404, detail="Platform not found")
    slug = str(row["slug"])
    base = PlatformResponse(
        platform_id=row["platform_id"],
        slug=slug,
        label=row["label"],
        active=row["active"],
        builtin=False,
        created_at=row["created_at"],
        login_url=row.get("login_url") or None,
    )
    return _enrich(slug, base)


@router.delete("/{platform_id}")
def delete_platform(platform_id: int, _user: dict = Depends(get_current_user)) -> dict:
    ok = platform_registry_service.delete_platform(platform_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Platform not found")
    return {"deleted": True}
