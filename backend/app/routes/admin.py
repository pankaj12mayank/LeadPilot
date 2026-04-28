from __future__ import annotations

from typing import Any, Dict, List

import config
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from backend.app.api.deps import get_current_admin
from backend.app.middleware.jwt import create_access_token
from backend.services import analytics_service, auth_service, branding_files, runtime_settings, settings_service
from database.orm.bootstrap import get_session_factory
from database.orm.models import Company

router = APIRouter(prefix="/admin", tags=["admin"])

_MAX_BRANDING_BYTES = 2 * 1024 * 1024


class AdminLoginBody(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


@router.post("/login")
def admin_login(body: AdminLoginBody) -> Dict[str, Any]:
    if not getattr(config, "ADMIN_EMAIL", "") or not getattr(config, "ADMIN_PASSWORD", ""):
        raise HTTPException(
            status_code=503,
            detail="Admin console is disabled. Set ADMIN_EMAIL and ADMIN_PASSWORD in the server environment.",
        )
    em = body.email.strip().lower()
    pw = body.password.strip()
    if em != config.ADMIN_EMAIL or pw != config.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin email or password")
    token = create_access_token("admin-console", {"admin": True})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/users")
def admin_list_users(_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return {"users": auth_service.list_users()}


class AdminCreateUserBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=128)


@router.post("/users")
def admin_create_user(body: AdminCreateUserBody, _admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    try:
        user = auth_service.create_user(body.email.strip().lower(), body.password)
    except ValueError as e:
        if str(e) == "email_taken":
            raise HTTPException(status_code=400, detail="Email already registered") from None
        raise HTTPException(status_code=400, detail="Could not create user") from e
    return {"user": user}


class AdminBulkDeleteUsersBody(BaseModel):
    ids: List[str] = Field(..., min_length=1, max_length=500)


@router.post("/users/bulk-delete")
def admin_bulk_delete_users(
    body: AdminBulkDeleteUsersBody,
    _admin: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    deleted = auth_service.delete_users(body.ids)
    return {"deleted": deleted}


class AdminUserActiveBody(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}")
def admin_patch_user(
    user_id: str,
    body: AdminUserActiveBody,
    _admin: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    updated = auth_service.set_user_active(user_id, body.is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": updated}


class AdminUserPasswordBody(BaseModel):
    password: str = Field(..., min_length=8, max_length=128)


@router.post("/users/{user_id}/password")
def admin_set_user_password(
    user_id: str,
    body: AdminUserPasswordBody,
    _admin: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    ok = auth_service.set_user_password(user_id, body.password)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


@router.get("/stats")
def admin_workspace_stats(_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    """High-level workspace metrics (same aggregates as the user dashboard)."""
    dash = analytics_service.dashboard(use_cache=True)
    users = auth_service.list_users()
    active_users = sum(1 for u in users if u.get("is_active"))
    Session = get_session_factory()
    db = Session()
    try:
        total_companies = int(db.scalar(select(func.count(Company.id))) or 0)
    finally:
        db.close()
    return {
        "registered_users": len(users),
        "active_users": active_users,
        "inactive_users": max(0, len(users) - active_users),
        "total_companies": total_companies,
        "total_leads": int(dash.get("total_leads") or dash.get("total") or 0),
        "hot_leads": int(dash.get("hot_leads") or 0),
        "contacted_leads": int(dash.get("contacted_leads") or 0),
        "converted_leads": int(dash.get("converted_leads") or 0),
        "conversion_rate_percent": float(dash.get("conversion_rate_percent") or 0),
    }


class AdminScoringWeights(BaseModel):
    role_relevance: int = Field(default=30, ge=1, le=100)
    company_size: int = Field(default=20, ge=1, le=100)
    signals: int = Field(default=25, ge=1, le=100)
    data_completeness: int = Field(default=15, ge=1, le=100)
    base_factor_mix: int = Field(default=10, ge=1, le=100)


class AdminTargetingFilters(BaseModel):
    allowed_sources: List[str] = Field(default_factory=lambda: ["yc", "job_board", "local", "crunchbase", "builtwith", "manual"])
    min_company_score: int = Field(default=70, ge=0, le=100)
    preferred_locations: List[str] = Field(default_factory=list)
    preferred_keywords: List[str] = Field(default_factory=list)

    @field_validator("allowed_sources")
    @classmethod
    def v_sources(cls, vals: List[str]) -> List[str]:
        out: list[str] = []
        for v in vals:
            x = (v or "").strip().lower().replace("-", "_")
            if x and x not in out:
                out.append(x)
        return out


class AdminControlPatch(BaseModel):
    scoring_weights: AdminScoringWeights | None = None
    targeting_filters: AdminTargetingFilters | None = None


@router.get("/controls")
def admin_get_controls(_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return runtime_settings.get_admin_controls()


@router.patch("/controls")
def admin_patch_controls(
    body: AdminControlPatch,
    _admin: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    updates: Dict[str, Any] = {"admin_controls": runtime_settings.get_admin_controls()}
    if body.scoring_weights is not None:
        updates["admin_controls"]["scoring_weights"] = body.scoring_weights.model_dump()
    if body.targeting_filters is not None:
        updates["admin_controls"]["targeting_filters"] = body.targeting_filters.model_dump()
    settings_service.patch_settings(updates)
    return runtime_settings.get_admin_controls()


@router.get("/branding")
def admin_get_branding(_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return runtime_settings.get_branding()


class BrandingPatch(BaseModel):
    product_name: str | None = None
    logo_url: str | None = None
    favicon_url: str | None = None
    footer_copyright: str | None = Field(None, max_length=280)


@router.patch("/branding")
def admin_patch_branding(
    body: BrandingPatch,
    _admin: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    if body.product_name is not None:
        patch["product_name"] = body.product_name.strip() or "LeadPilot"
    if body.logo_url is not None:
        patch["logo_url"] = body.logo_url.strip()
    if body.favicon_url is not None:
        patch["favicon_url"] = body.favicon_url.strip()
    if body.footer_copyright is not None:
        patch["footer_copyright"] = body.footer_copyright.strip()[:280]
    settings_service.patch_settings({"branding": patch})
    return runtime_settings.get_branding()


@router.post("/branding/upload-logo")
async def admin_upload_logo(
    file: UploadFile = File(...),
    _admin: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    raw = await file.read()
    if len(raw) > _MAX_BRANDING_BYTES:
        raise HTTPException(status_code=413, detail="Logo file too large (max 2 MB)")
    try:
        url = branding_files.save_branding_logo(file.filename or "logo.png", raw)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Unsupported logo type. Use PNG, JPG, JPEG, WebP, SVG, or GIF.",
        ) from None
    settings_service.patch_settings({"branding": {"logo_url": url}})
    return runtime_settings.get_branding()


@router.post("/branding/upload-favicon")
async def admin_upload_favicon(
    file: UploadFile = File(...),
    _admin: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    raw = await file.read()
    if len(raw) > _MAX_BRANDING_BYTES:
        raise HTTPException(status_code=413, detail="Favicon file too large (max 2 MB)")
    try:
        url = branding_files.save_branding_favicon(file.filename or "favicon.ico", raw)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Unsupported favicon type. Use ICO, PNG, or SVG.",
        ) from None
    settings_service.patch_settings({"branding": {"favicon_url": url}})
    return runtime_settings.get_branding()


@router.post("/branding/clear-logo")
def admin_clear_logo(_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    branding_files.clear_branding_logo()
    settings_service.patch_settings({"branding": {"logo_url": ""}})
    return runtime_settings.get_branding()


@router.post("/branding/clear-favicon")
def admin_clear_favicon(_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    branding_files.clear_branding_favicon()
    settings_service.patch_settings({"branding": {"favicon_url": ""}})
    return runtime_settings.get_branding()
