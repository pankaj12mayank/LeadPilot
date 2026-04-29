from __future__ import annotations

import json
from typing import Any, Dict, List
from pathlib import Path
from datetime import datetime, timezone

import config
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from backend.app.api.deps import get_current_admin
from backend.app.middleware.jwt import create_access_token
from backend.services import analytics_service, auth_service, branding_files, runtime_settings, settings_service
from database.orm.bootstrap import get_session_factory
from database.orm.models import Company, LeadPack

router = APIRouter(prefix="/admin", tags=["admin"])

_MAX_BRANDING_BYTES = 2 * 1024 * 1024


class AdminLoginBody(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class AdminLeadPackCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    lead_ids: List[str] = Field(default_factory=list)
    price_usd: float = Field(default=0.0, ge=0.0)
    is_active: bool = True


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


@router.get("/lead-packs")
def admin_list_lead_packs(_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        rows = list(db.scalars(select(LeadPack).order_by(LeadPack.created_at.desc())))
        return {
            "items": [
                {
                    "id": x.id,
                    "name": x.name,
                    "description": x.description or "",
                    "lead_ids": json.loads(x.lead_ids_json or "[]"),
                    "price_usd": float(x.price_usd or 0),
                    "is_active": bool(int(x.is_active or 0)),
                    "created_at": x.created_at,
                    "updated_at": x.updated_at,
                }
                for x in rows
            ]
        }
    finally:
        db.close()


@router.post("/lead-packs")
def admin_create_lead_pack(body: AdminLeadPackCreate, admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        row = LeadPack(
            name=body.name.strip(),
            description=body.description.strip(),
            lead_ids_json=json.dumps([str(x).strip() for x in body.lead_ids if str(x).strip()], ensure_ascii=False),
            price_usd=float(body.price_usd or 0),
            is_active=1 if body.is_active else 0,
            created_by=str(admin.get("sub") or "admin"),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"ok": True, "id": row.id}
    finally:
        db.close()


@router.patch("/lead-packs/{pack_id}")
def admin_patch_lead_pack(pack_id: int, body: AdminLeadPackCreate, _admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        row = db.get(LeadPack, int(pack_id))
        if row is None:
            raise HTTPException(status_code=404, detail="Lead pack not found")
        row.name = body.name.strip()
        row.description = body.description.strip()
        row.lead_ids_json = json.dumps([str(x).strip() for x in body.lead_ids if str(x).strip()], ensure_ascii=False)
        row.price_usd = float(body.price_usd or 0)
        row.is_active = 1 if body.is_active else 0
        row.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.get("/users")
def admin_list_users(_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return {"users": auth_service.list_users()}


class AdminCreateUserBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="user")
    plan_id: str = Field(default="starter")


@router.post("/users")
def admin_create_user(body: AdminCreateUserBody, _admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    try:
        user = auth_service.create_user(body.email.strip().lower(), body.password, role=body.role, plan_id=body.plan_id)
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
    role: str | None = None
    plan_id: str | None = None


@router.patch("/users/{user_id}")
def admin_patch_user(
    user_id: str,
    body: AdminUserActiveBody,
    _admin: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    updated = auth_service.set_user_active(user_id, body.is_active)
    if updated and body.role is not None:
        updated = auth_service.set_user_role(user_id, body.role)
    if updated and body.plan_id is not None:
        updated = auth_service.set_user_plan(user_id, body.plan_id)
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
    schedule_timing: dict[str, str] | None = None


class AdminTargetingConfig(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)
    company_types: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    preferred_keywords: List[str] = Field(default_factory=list)
    min_company_score: int = Field(default=70, ge=0, le=100)


class AdminSourcesConfig(BaseModel):
    job_boards: bool = True
    startup_directories: bool = True
    local_listings: bool = True
    manual_seeds: bool = True
    linkedin: bool = True
    public_db: bool = True
    google_maps: bool = True
    indiamart: bool = True
    justdial: bool = True
    eworldtrade: bool = True
    global_sources: bool = True
    thomasnet: bool = True
    yelp: bool = True
    faire: bool = True
    allowed_sources: List[str] = Field(
        default_factory=lambda: [
            "linkedin",
            "yc",
            "job_board",
            "local",
            "crunchbase",
            "builtwith",
            "google_maps",
            "indiamart",
            "justdial",
            "eworldtrade",
            "global_sources",
            "thomasnet",
            "yelp",
            "faire",
            "manual",
        ]
    )

    @field_validator("allowed_sources")
    @classmethod
    def v_allowed_sources(cls, vals: List[str]) -> List[str]:
        out: list[str] = []
        for v in vals:
            x = (v or "").strip().lower().replace("-", "_")
            if x and x not in out:
                out.append(x)
        return out


class AdminScoringConfig(BaseModel):
    role_weight: int = Field(default=40, ge=1, le=100)
    signal_weight: int = Field(default=35, ge=1, le=100)
    data_weight: int = Field(default=25, ge=1, le=100)
    company_size_weight: int = Field(default=20, ge=1, le=100)
    base_factor_mix: int = Field(default=10, ge=1, le=100)


class AdminSignalsConfig(BaseModel):
    hiring_enabled: bool = True
    scaling_enabled: bool = True


class AdminSchedulerConfig(BaseModel):
    daily_time: str = "02:00"
    weekly_time: str = "03:00"
    linkedin_day: str = "sat"
    daily_auto: str = "0 2 * * *"
    friday_heavy: str = "0 3 * * 5"
    saturday_linkedin: str = "0 10 * * 6"
    sunday_report: str = "0 18 * * 0"

    @field_validator("linkedin_day")
    @classmethod
    def v_day(cls, v: str) -> str:
        x = (v or "sat").strip().lower()[:3]
        return x if x in {"mon", "tue", "wed", "thu", "fri", "sat", "sun"} else "sat"


class AdminSessionPolicy(BaseModel):
    expiry_days: int = Field(default=7, ge=1, le=365)


class AdminRetryPolicy(BaseModel):
    retry_count: int = Field(default=3, ge=1, le=10)


class AdminTaskPriority(BaseModel):
    linkedin: str = Field(default="high")
    scoring: str = Field(default="high")
    enrichment: str = Field(default="medium")
    ingestion: str = Field(default="low")

    @field_validator("linkedin", "scoring", "enrichment", "ingestion")
    @classmethod
    def v_priority(cls, v: str) -> str:
        x = (v or "").strip().lower()
        if x not in {"high", "medium", "low"}:
            raise ValueError("priority must be high/medium/low")
        return x


class AdminSourceRegistryEntry(BaseModel):
    source_name: str = Field(..., min_length=1)
    source_type: str = Field(default="directory")
    enabled: bool = True
    input_type: str = Field(default="url")
    adapter_function: str = Field(default="collect_companies_from_source_pages", min_length=1)

    @field_validator("source_name")
    @classmethod
    def v_source_name(cls, v: str) -> str:
        x = (v or "").strip().lower().replace("-", "_")
        if not x:
            raise ValueError("source_name is required")
        return x

    @field_validator("source_type")
    @classmethod
    def v_source_type(cls, v: str) -> str:
        x = (v or "").strip().lower().replace("-", "_")
        if x not in {"job_board", "directory", "local", "manual", "marketplace"}:
            raise ValueError("source_type must be job_board/directory/local/manual/marketplace")
        return x

    @field_validator("input_type")
    @classmethod
    def v_input_type(cls, v: str) -> str:
        x = (v or "").strip().lower()
        if x not in {"url", "keyword", "file", "csv"}:
            raise ValueError("input_type must be url/keyword/file/csv")
        return x

    @field_validator("adapter_function")
    @classmethod
    def v_adapter_function(cls, v: str) -> str:
        x = (v or "").strip()
        if not x:
            raise ValueError("adapter_function is required")
        return x


class AdminWorkerConfig(BaseModel):
    worker_count: int = Field(default=3, ge=1, le=64)


class AdminAiControl(BaseModel):
    ollama_enabled: bool = True
    api_enabled: bool = True


class AdminScoringControl(BaseModel):
    role: int = Field(default=40, ge=1, le=100)
    signals: int = Field(default=35, ge=1, le=100)
    ai_score: int = Field(default=25, ge=1, le=100)


class AdminSafetyControl(BaseModel):
    delay_seconds: float = Field(default=1.0, ge=0.2, le=8.0)
    batch_size: int = Field(default=10, ge=1, le=100)
    retry_count: int = Field(default=3, ge=1, le=10)
    pagination_limit: int = Field(default=5, ge=1, le=100)


class AdminQueuePriority(BaseModel):
    linkedin: str = Field(default="high")
    ai: str = Field(default="high")
    others: str = Field(default="medium")

    @field_validator("linkedin", "ai", "others")
    @classmethod
    def v_q_priority(cls, v: str) -> str:
        x = (v or "").strip().lower()
        if x not in {"high", "medium", "low"}:
            raise ValueError("priority must be high/medium/low")
        return x


class AdminPlanChannelPolicy(BaseModel):
    channels: List[str] = Field(default_factory=list)
    lead_limit: int = Field(default=100, ge=1, le=100000)

    @field_validator("channels")
    @classmethod
    def v_channels(cls, vals: List[str]) -> List[str]:
        out: list[str] = []
        for v in vals:
            x = (v or "").strip().lower().replace("-", "_")
            if x and x not in out:
                out.append(x)
        return out


class AdminConfigPatch(BaseModel):
    targeting: AdminTargetingConfig | None = None
    sources: AdminSourcesConfig | None = None
    scoring_weights: AdminScoringConfig | None = None
    signals_config: AdminSignalsConfig | None = None
    scheduler_config: AdminSchedulerConfig | None = None
    session_policy: AdminSessionPolicy | None = None
    retry_policy: AdminRetryPolicy | None = None
    task_priority: AdminTaskPriority | None = None
    source_registry: List[AdminSourceRegistryEntry] | None = None
    worker_config: AdminWorkerConfig | None = None
    ai_control: AdminAiControl | None = None
    scoring_control: AdminScoringControl | None = None
    safety_control: AdminSafetyControl | None = None
    queue_priority: AdminQueuePriority | None = None
    plan_channel_access: Dict[str, AdminPlanChannelPolicy] | None = None


def _job_logs_path() -> Path:
    root = Path(config.SESSIONS_DIR) / "job_logs"
    root.mkdir(parents=True, exist_ok=True)
    return root / "job_runs.jsonl"


@router.get("/job-logs")
def admin_get_job_logs(limit: int = 100, _admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    lim = max(1, min(int(limit or 100), 500))
    p = _job_logs_path()
    if not p.exists():
        return {"count": 0, "items": []}
    rows: list[dict[str, Any]] = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                rows.append(json.loads(s))
            except Exception:
                continue
    rows = rows[-lim:]
    rows.reverse()
    return {"count": len(rows), "items": rows}


@router.get("/controls")
def admin_get_controls(_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return runtime_settings.get_admin_controls()


@router.patch("/controls")
def admin_patch_controls(
    body: AdminControlPatch,
    _admin: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    current = runtime_settings.get_admin_config()
    updates: Dict[str, Any] = {"admin_config": dict(current)}
    if body.scoring_weights is not None:
        scoring = dict(current.get("scoring_weights") or {})
        scoring.update(
            {
                "role_weight": body.scoring_weights.role_relevance,
                "company_size_weight": body.scoring_weights.company_size,
                "signal_weight": body.scoring_weights.signals,
                "data_weight": body.scoring_weights.data_completeness,
                "base_factor_mix": body.scoring_weights.base_factor_mix,
            }
        )
        updates["admin_config"]["scoring_weights"] = scoring
    if body.targeting_filters is not None:
        targeting = dict(current.get("targeting") or {})
        targeting.update(
            {
                "preferred_locations": body.targeting_filters.preferred_locations,
                "preferred_keywords": body.targeting_filters.preferred_keywords,
                "min_company_score": body.targeting_filters.min_company_score,
            }
        )
        updates["admin_config"]["targeting"] = targeting
        sources = dict(current.get("sources") or {})
        sources["allowed_sources"] = body.targeting_filters.allowed_sources
        updates["admin_config"]["sources"] = sources
        allowed = set(body.targeting_filters.allowed_sources)
        registry = []
        for item in runtime_settings.get_source_registry():
            entry = dict(item)
            name = str(entry.get("source_name") or "").strip().lower()
            if name:
                entry["enabled"] = name in allowed
            registry.append(entry)
        updates["admin_config"]["source_registry"] = registry
    if body.schedule_timing is not None:
        cur = current.get("scheduler_config") or {}
        merged = {
            "daily_auto": str(body.schedule_timing.get("daily_auto") or cur.get("daily_auto") or "0 2 * * *"),
            "friday_heavy": str(body.schedule_timing.get("friday_heavy") or cur.get("friday_heavy") or "0 3 * * 5"),
            "saturday_linkedin": str(
                body.schedule_timing.get("saturday_linkedin") or cur.get("saturday_linkedin") or "0 10 * * 6"
            ),
            "sunday_report": str(body.schedule_timing.get("sunday_report") or cur.get("sunday_report") or "0 18 * * 0"),
        }
        scheduler = dict(cur)
        scheduler.update(merged)
        updates["admin_config"]["scheduler_config"] = scheduler
    settings_service.patch_settings(updates)
    return runtime_settings.get_admin_controls()


@router.get("/config")
def admin_get_config(_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return runtime_settings.get_admin_config()


@router.patch("/config")
def admin_patch_config(
    body: AdminConfigPatch,
    _admin: dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    cur = runtime_settings.get_admin_config()
    nxt = dict(cur)
    if body.targeting is not None:
        nxt["targeting"] = body.targeting.model_dump()
    if body.sources is not None:
        nxt["sources"] = body.sources.model_dump()
    if body.scoring_weights is not None:
        nxt["scoring_weights"] = body.scoring_weights.model_dump()
    if body.signals_config is not None:
        nxt["signals_config"] = body.signals_config.model_dump()
    if body.scheduler_config is not None:
        nxt["scheduler_config"] = body.scheduler_config.model_dump()
    if body.session_policy is not None:
        nxt["session_policy"] = body.session_policy.model_dump()
    if body.retry_policy is not None:
        nxt["retry_policy"] = body.retry_policy.model_dump()
    if body.task_priority is not None:
        nxt["task_priority"] = body.task_priority.model_dump()
    if body.source_registry is not None:
        nxt["source_registry"] = [item.model_dump() for item in body.source_registry]
    if body.worker_config is not None:
        nxt["worker_config"] = body.worker_config.model_dump()
    if body.ai_control is not None:
        nxt["ai_control"] = body.ai_control.model_dump()
    if body.scoring_control is not None:
        nxt["scoring_control"] = body.scoring_control.model_dump()
    if body.safety_control is not None:
        nxt["safety_control"] = body.safety_control.model_dump()
    if body.queue_priority is not None:
        nxt["queue_priority"] = body.queue_priority.model_dump()
    if body.plan_channel_access is not None:
        nxt["plan_channel_access"] = {k: v.model_dump() for k, v in body.plan_channel_access.items()}
    settings_service.patch_settings({"admin_config": nxt})
    return runtime_settings.get_admin_config()


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
