from __future__ import annotations

from typing import Any, List
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.leadpilot.linkedin_session_cache import session_info_dict
from backend.services import lead_orm_service
from backend.services import (
    company_enrichment_service,
    company_ingestion_service,
    company_service,
    company_weekly_engine,
    runtime_settings,
    settings_service,
)
from database.orm.models import Company, CompanyEnrichment, Lead

router = APIRouter(prefix="/companies", tags=["companies"])


def _insert_company_rows_into_leads(db: Session, rows: list[dict[str, Any]], *, owner_user_id: str) -> dict[str, int]:
    created = 0
    skipped = 0
    for row in rows:
        website = str(row.get("website") or "").strip().lower()
        company_name = str(row.get("company_name") or "").strip()
        source = str(row.get("source") or "public_db").strip().lower()
        if not website or not company_name:
            skipped += 1
            continue
        existing = db.scalar(
            select(Lead).where(
                func.lower(Lead.company_website) == website,
                func.lower(Lead.source_platform) == source,
                Lead.user_id == str(owner_user_id or ""),
            )
        )
        if existing is not None:
            skipped += 1
            continue
        lead_orm_service.create_lead(
            db,
            {
                "full_name": f"Decision Maker - {company_name}",
                "title": "Decision Maker",
                "company_name": company_name,
                "company_website": website,
                "source_platform": source,
                "notes": f"Auto-created from company ingestion source={source}",
                "user_id": owner_user_id,
            },
        )
        created += 1
    return {"created": created, "skipped": skipped}


@router.get("/user-config")
def get_user_config(
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    scoped = runtime_settings.apply_plan_access_to_admin_config(
        runtime_settings.get_admin_config(),
        role=str(_user.get("role") or "user"),
        plan_id=str(_user.get("plan_id") or "starter"),
    )
    return {
        "admin_config": scoped,
        "config_event": runtime_settings.get_last_config_event(),
    }


@router.get("/task-classification")
def task_classification(
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    STEP W2: task tags for login requirements.
    """
    rows = []
    for name in sorted(company_weekly_engine.TASK_CLASSIFICATION.keys()):
        rows.append(company_weekly_engine.classify_task(name))
    return {"items": rows}


class CompanyIngestItem(BaseModel):
    company_name: str | None = None
    name: str | None = None
    website: str | None = None
    domain: str | None = None
    source: str | None = None
    signals: list[str] | dict[str, Any] | None = None
    ai_score: float | None = None


class CompanyIngestRequest(BaseModel):
    companies: List[CompanyIngestItem] = Field(default_factory=list)
    source: str = "manual"


class CompanyRealIngestRequest(BaseModel):
    source: str = Field(default="manual")
    sources: List[str] = Field(default_factory=list)
    seed_urls: List[str] = Field(default_factory=list)
    batch_size: int = Field(default=10, ge=10, le=20)
    delay_seconds: float = Field(default=1.0, ge=0.2, le=8.0)
    max_companies: int = Field(default=200, ge=1, le=2000)
    enrich_after_ingest: bool = True
    enrich_limit: int = Field(default=20, ge=1, le=100)
    enrich_timeout_seconds: float = Field(default=10.0, ge=2.0, le=30.0)

    @field_validator("source")
    @classmethod
    def v_source(cls, v: str) -> str:
        x = (v or "").strip().lower().replace("-", "_")
        available_sources = set(runtime_settings.get_real_ingestion_source_names()) or (
            set(company_ingestion_service.SUPPORTED_REAL_SOURCES) - {"manual"}
        )
        if x not in available_sources:
            allowed = ", ".join(sorted(available_sources))
            raise ValueError(f"Unsupported source {v!r}; expected one of: {allowed}")
        return x

    @field_validator("sources")
    @classmethod
    def v_sources(cls, vals: List[str]) -> List[str]:
        available_sources = set(runtime_settings.get_real_ingestion_source_names()) or (
            set(company_ingestion_service.SUPPORTED_REAL_SOURCES) - {"manual"}
        )
        out: list[str] = []
        seen: set[str] = set()
        for raw in vals:
            x = (raw or "").strip().lower().replace("-", "_")
            if not x or x == "manual" or x not in available_sources or x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out


class ExplorerSearchRequest(BaseModel):
    mode: str = Field(default="explorer", description="linkedin | explorer")
    keyword: str = ""
    location: str = ""
    source_filter: str = Field(default="all")
    updated_within_days: int = Field(default=0, ge=0, le=365)
    min_score: float = Field(default=0.0, ge=0.0, le=100.0)
    signal_hiring: bool = False
    signal_scaling: bool = False
    min_results: int = Field(default=10, ge=1, le=200)
    max_results: int = Field(default=50, ge=1, le=500)
    sources: List[str] = Field(default_factory=lambda: ["yc", "job_board", "local", "crunchbase", "builtwith"])
    batch_size: int = Field(default=10, ge=10, le=20)
    delay_seconds: float = Field(default=1.0, ge=0.2, le=8.0)
    max_companies_per_source: int = Field(default=80, ge=1, le=500)
    enrich_after_ingest: bool = True
    enrich_limit: int = Field(default=20, ge=1, le=100)
    enrich_timeout_seconds: float = Field(default=10.0, ge=2.0, le=30.0)

    @field_validator("mode")
    @classmethod
    def v_mode(cls, v: str) -> str:
        x = (v or "explorer").strip().lower()
        if x not in ("linkedin", "explorer"):
            raise ValueError("mode must be 'linkedin' or 'explorer'")
        return x

    @field_validator("source_filter")
    @classmethod
    def v_source_filter(cls, v: str) -> str:
        x = (v or "all").strip().lower().replace("-", "_")
        if x == "all":
            return x
        available_sources = set(runtime_settings.get_real_ingestion_source_names()) or (
            set(company_ingestion_service.SUPPORTED_REAL_SOURCES) - {"manual"}
        )
        if x not in available_sources:
            allowed = ", ".join(["all", *sorted(available_sources)])
            raise ValueError(f"source_filter must be one of: {allowed}")
        return x

    @field_validator("sources")
    @classmethod
    def v_sources(cls, vals: List[str]) -> List[str]:
        available_sources = set(runtime_settings.get_real_ingestion_source_names()) or (
            set(company_ingestion_service.SUPPORTED_REAL_SOURCES) - {"manual"}
        )
        out: list[str] = []
        for raw in vals:
            x = (raw or "").strip().lower().replace("-", "_")
            if x in available_sources and x != "manual":
                out.append(x)
        return out


class DirectoryFetchRequest(BaseModel):
    source: str = Field(...)
    keyword: str = Field(..., min_length=1)
    location: str = Field(default="")
    batch_size: int = Field(default=10, ge=1, le=100)
    delay_seconds: float = Field(default=1.0, ge=0.2, le=8.0)
    max_companies: int = Field(default=120, ge=1, le=2000)

    @field_validator("source")
    @classmethod
    def v_source(cls, v: str) -> str:
        x = (v or "").strip().lower().replace("-", "_")
        available_sources = set(runtime_settings.get_real_ingestion_source_names()) or (
            set(company_ingestion_service.SUPPORTED_REAL_SOURCES) - {"manual"}
        )
        if x not in available_sources:
            allowed = ", ".join(sorted(available_sources))
            raise ValueError(f"Unsupported source {v!r}; expected one of: {allowed}")
        return x


class CustomSourceCreateRequest(BaseModel):
    source_name: str = Field(..., min_length=1, max_length=64)
    input_type: str = Field(..., min_length=1)

    @field_validator("source_name")
    @classmethod
    def v_source_name(cls, v: str) -> str:
        x = (v or "").strip().lower().replace("-", "_")
        if not x:
            raise ValueError("source_name is required")
        if not all(ch.isalnum() or ch == "_" for ch in x):
            raise ValueError("source_name must use letters, numbers, or underscores")
        return x

    @field_validator("input_type")
    @classmethod
    def v_input_type(cls, v: str) -> str:
        x = (v or "").strip().lower()
        if x not in {"url", "keyword", "csv"}:
            raise ValueError("input_type must be url/keyword/csv")
        return x


@router.get("")
@router.get("/", include_in_schema=False)
def list_companies(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
    source: str = "all",
    updated_within_days: int = 0,
) -> list[dict[str, Any]]:
    rows = company_service.list_companies_filtered(db, source_filter=source, updated_within_days=updated_within_days, limit=500)
    return [company_service.company_to_dict(x) for x in rows]


@router.get("/stale")
def list_stale_public_companies(
    stale_days: int = 7,
    limit: int = 200,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    rows = company_service.list_stale_companies(db, stale_days=stale_days, limit=limit)
    return {"count": len(rows), "items": [company_service.company_to_dict(x) for x in rows], "stale_days": stale_days}


@router.get("/by-domain/{domain}")
def get_company(
    domain: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    row = company_service.get_company_by_domain(db, domain)
    if row is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company_service.company_to_dict(row)


@router.post("/custom-sources")
def create_custom_source(
    body: CustomSourceCreateRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    source_name = body.source_name
    if runtime_settings.get_source_registry_entry(source_name) is not None:
        raise HTTPException(status_code=400, detail="Source already exists")

    current = runtime_settings.get_admin_config()
    source_registry = list(current.get("source_registry") or [])
    source_registry.append(
        {
            "source_name": source_name,
            "source_type": "manual" if body.input_type == "csv" else "directory",
            "enabled": True,
            "input_type": body.input_type,
            "adapter_function": "ingest_public_companies" if body.input_type == "csv" else "collect_companies_from_source_pages",
        }
    )
    sources_cfg = dict(current.get("sources") or {})
    allowed_sources = list(sources_cfg.get("allowed_sources") or [])
    if source_name not in allowed_sources:
        allowed_sources.append(source_name)
    sources_cfg["allowed_sources"] = allowed_sources
    settings_service.patch_settings(
        {
            "admin_config": {
                **current,
                "sources": sources_cfg,
                "source_registry": source_registry,
            }
        }
    )
    return {
        "ok": True,
        "source": runtime_settings.get_source_registry_entry(source_name),
        "registered_by": str(user.get("email") or user.get("sub") or "user"),
    }


@router.post("/ingest")
def ingest_companies(
    body: CompanyIngestRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, int]:
    stats = company_service.ingest_public_companies(
        db,
        [x.model_dump(exclude_none=True) for x in body.companies],
        default_source=body.source,
    )
    db.commit()
    return stats


@router.post("/ingest-real")
def ingest_companies_real_sources(
    body: CompanyRealIngestRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Step-2 real-source ingestion:
    - Select source
    - Fetch in small batches (10-20), delayed between requests
    - Extract website/domain candidates from source pages
    - Upsert into Company DB
    """
    requested_sources = body.sources or [body.source]
    if not requested_sources or any(src == "manual" for src in requested_sources):
        raise HTTPException(
            status_code=400,
            detail="For manual seeds use /companies/ingest. /ingest-real expects source pages.",
        )
    enabled_sources = set(runtime_settings.get_enabled_ingestion_sources())
    filtered_sources = [src for src in requested_sources if src in enabled_sources]
    if not filtered_sources:
        raise HTTPException(status_code=400, detail="No enabled ingestion sources selected")
    requested_sources = filtered_sources

    ingest_flow = company_ingestion_service.ingest_from_sources(
        db=db,
        sources=requested_sources,
        shared_source_input={
            "seed_urls": body.seed_urls,
            "batch_size": body.batch_size,
            "delay_seconds": body.delay_seconds,
            "max_companies": body.max_companies,
        },
        delay_between_sources=body.delay_seconds,
    )
    fetch_stats = ingest_flow.get("fetched_total") or {"pages_ok": 0, "pages_failed": 0, "candidates": 0}
    save_stats = ingest_flow.get("saved_total") or {"created": 0, "updated": 0, "skipped": 0}
    lead_stats_total = {"created": 0, "skipped": 0}
    for run in ingest_flow.get("runs") or []:
        rows = run.get("rows") if isinstance(run, dict) else []
        if isinstance(rows, list):
            lead_stats = _insert_company_rows_into_leads(db, rows, owner_user_id=str(_user.get("id") or ""))
            lead_stats_total["created"] += int(lead_stats.get("created") or 0)
            lead_stats_total["skipped"] += int(lead_stats.get("skipped") or 0)
    enrich_stats: dict[str, Any] | None = None
    if body.enrich_after_ingest:
        enrich_stats = company_enrichment_service.enrich_companies_batch(
            db,
            limit=body.enrich_limit,
            timeout_seconds=body.enrich_timeout_seconds,
            delay_seconds=min(2.0, body.delay_seconds),
        )
    db.commit()
    return {
        "source": body.source,
        "sources": ingest_flow.get("sources") or requested_sources,
        "fetched": fetch_stats,
        "saved": save_stats,
        "leads_saved": lead_stats_total,
        "company_saved": save_stats,
        "lead_saved": lead_stats_total,
        "runs": ingest_flow.get("runs") or [],
        "failed_sources": int(ingest_flow.get("failed_sources") or 0),
        "quality_skips": ingest_flow.get("quality_skips_total")
        or {"missing_website": 0, "duplicate_domain": 0, "invalid_url": 0, "short_content": 0},
        "errors": ingest_flow.get("errors") or [],
        "enrichment": enrich_stats,
    }


@router.post("/explorer/search")
def explorer_search_companies(
    body: ExplorerSearchRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Explorer mode (Apollo-lite):
    - Search company DB by keyword/location
    - If insufficient results, trigger real-source ingestion
    - Retry query and return the final result set
    """
    if body.mode == "linkedin":
        return {
            "mode": "linkedin",
            "keyword": body.keyword,
            "location": body.location,
            "count": 0,
            "results": [],
            "note": "LinkedIn mode uses existing LinkedIn capture flow.",
        }

    cfg = runtime_settings.get_admin_config()
    tgt = cfg.get("targeting") or {}
    sig_cfg = cfg.get("signals_config") or {}
    resolved_keyword = str(body.keyword or "").strip()
    if not resolved_keyword:
        ks = [str(x).strip() for x in (tgt.get("keywords") or []) if str(x).strip()]
        inds = [str(x).strip() for x in (tgt.get("industries") or []) if str(x).strip()]
        ctypes = [str(x).strip() for x in (tgt.get("company_types") or []) if str(x).strip()]
        resolved_keyword = " ".join((ks + inds + ctypes)[:3]).strip()
    resolved_location = str(body.location or "").strip()
    if not resolved_location:
        locs = [str(x).strip() for x in (tgt.get("locations") or []) if str(x).strip()]
        if locs:
            resolved_location = locs[0]

    kw = str(body.keyword or "").strip().lower()
    loc = str(body.location or "").strip().lower()
    enabled_sources = [s for s in runtime_settings.get_enabled_ingestion_sources() if s != "manual"]
    chosen_sources = [s for s in body.sources if s in enabled_sources]
    if not chosen_sources:
        chosen_sources = [s for s in ["yc", "job_board", "local"] if s in enabled_sources]
    requested_source_filter = str(body.source_filter or "all").strip().lower().replace("-", "_")
    effective_source_filter = requested_source_filter if requested_source_filter in enabled_sources else "all"
    allow_hiring_filter = bool(sig_cfg.get("hiring_enabled", True))
    allow_scaling_filter = bool(sig_cfg.get("scaling_enabled", True))
    effective_signal_hiring = bool(body.signal_hiring) and allow_hiring_filter
    effective_signal_scaling = bool(body.signal_scaling) and allow_scaling_filter

    def _search_rows(limit: int) -> list[dict[str, Any]]:
        stmt = (
            select(Company, CompanyEnrichment)
            .outerjoin(CompanyEnrichment, CompanyEnrichment.company_id == Company.id)
        )
        if kw:
            term = f"%{kw}%"
            stmt = stmt.where(
                func.lower(Company.company_name).like(term)
                | func.lower(Company.domain).like(term)
                | func.lower(Company.website).like(term)
            )
        if loc:
            loc_term = f"%{loc}%"
            stmt = stmt.where(
                func.lower(Company.company_name).like(loc_term)
                | func.lower(Company.domain).like(loc_term)
                | func.lower(Company.website).like(loc_term)
            )
        if effective_source_filter != "all":
            stmt = stmt.where(func.lower(Company.source).like(f"%{effective_source_filter}%"))
        if int(body.updated_within_days or 0) > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=int(body.updated_within_days))
            stmt = stmt.where(Company.last_updated >= cutoff.replace(microsecond=0).isoformat())
        if float(body.min_score or 0) > 0:
            stmt = stmt.where(func.coalesce(CompanyEnrichment.score, 0.0) >= float(body.min_score))
        if effective_signal_hiring:
            stmt = stmt.where(func.coalesce(CompanyEnrichment.signal_hiring, 0) >= 1)
        if effective_signal_scaling:
            stmt = stmt.where(func.coalesce(CompanyEnrichment.signal_scaling, 0) >= 1)
        stmt = stmt.order_by(
            func.coalesce(CompanyEnrichment.score, 0.0).desc(),
            Company.id.desc(),
        ).limit(limit)
        rows: list[dict[str, Any]] = []
        for c, e in db.execute(stmt).all():
            rows.append(
                {
                    **company_service.company_to_dict(c),
                    "score": float(getattr(c, "ai_score", 0.0) or (e.score if e else 0.0) or 0.0),
                    "priority": (e.priority or "") if e else "",
                    "signals": {
                        "hiring": int(e.signal_hiring or 0) if e else int("hiring" in str(getattr(c, "signals", "") or "").split(",")),
                        "scaling": int(e.signal_scaling or 0) if e else int("scaling" in str(getattr(c, "signals", "") or "").split(",")),
                        "content_gap": int(e.signal_content_gap or 0) if e else int("content_gap" in str(getattr(c, "signals", "") or "").split(",")),
                        "ads_gap": int(e.signal_ads_gap or 0) if e else int("ads_gap" in str(getattr(c, "signals", "") or "").split(",")),
                    },
                }
            )
        return rows

    existing = _search_rows(body.max_results)
    fetch_runs: list[dict[str, Any]] = []
    saved_total = {"created": 0, "updated": 0, "skipped": 0}

    if len(existing) < body.min_results and chosen_sources:
        ingest_flow = company_ingestion_service.ingest_from_sources(
            db=db,
            sources=chosen_sources,
            source_input_factory=lambda src: {
                "seed_urls": company_ingestion_service.default_seed_urls_for_source(
                    source=src,
                    keyword=resolved_keyword,
                    location=resolved_location,
                ),
                "batch_size": body.batch_size,
                "delay_seconds": body.delay_seconds,
                "max_companies": body.max_companies_per_source,
            },
            delay_between_sources=body.delay_seconds,
        )
        fetch_runs = list(ingest_flow.get("runs") or [])
        saved_total = ingest_flow.get("saved_total") or saved_total
        quality_skips_total = ingest_flow.get("quality_skips_total") or {
            "missing_website": 0,
            "duplicate_domain": 0,
            "invalid_url": 0,
            "short_content": 0,
        }
        errors = ingest_flow.get("errors") or []
        enrich_stats: dict[str, Any] | None = None
        if body.enrich_after_ingest:
            enrich_stats = company_enrichment_service.enrich_companies_batch(
                db,
                limit=body.enrich_limit,
                timeout_seconds=body.enrich_timeout_seconds,
                delay_seconds=min(2.0, body.delay_seconds),
            )
        db.commit()
    else:
        enrich_stats = None
        quality_skips_total = {"missing_website": 0, "duplicate_domain": 0, "invalid_url": 0, "short_content": 0}
        errors = []

    final_rows = _search_rows(body.max_results)
    return {
        "mode": "explorer",
        "keyword": resolved_keyword,
        "location": resolved_location,
        "count": len(final_rows),
        "results": final_rows,
        "ingestion": {
            "triggered": len(existing) < body.min_results,
            "runs": fetch_runs,
            "saved_total": saved_total,
            "company_saved": saved_total,
            "quality_skips": quality_skips_total,
            "errors": errors,
            "enrichment": enrich_stats,
            "effective_sources": chosen_sources,
        },
        "effective_filters": {
            "source_filter": effective_source_filter,
            "signal_hiring": effective_signal_hiring,
            "signal_scaling": effective_signal_scaling,
            "enabled_signal_filters": {
                "hiring": allow_hiring_filter,
                "scaling": allow_scaling_filter,
            },
            "enabled_sources": enabled_sources,
        },
    }


@router.post("/directory/fetch")
def directory_fetch_leads(
    body: DirectoryFetchRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    enabled_sources = set(runtime_settings.get_enabled_ingestion_sources())
    if body.source not in enabled_sources:
        raise HTTPException(status_code=400, detail="Source disabled by admin/plan policy")
    seed_urls = company_ingestion_service.default_seed_urls_for_source(
        source=body.source,
        keyword=body.keyword,
        location=body.location,
    )
    flow = company_ingestion_service.ingest_from_sources(
        db=db,
        sources=[body.source],
        shared_source_input={
            "seed_urls": seed_urls,
            "batch_size": body.batch_size,
            "delay_seconds": body.delay_seconds,
            "max_companies": body.max_companies,
        },
        delay_between_sources=body.delay_seconds,
    )
    lead_stats_total = {"created": 0, "skipped": 0}
    for run in flow.get("runs") or []:
        rows = run.get("rows") if isinstance(run, dict) else []
        if isinstance(rows, list):
            lead_stats = _insert_company_rows_into_leads(db, rows, owner_user_id=str(user.get("id") or ""))
            lead_stats_total["created"] += int(lead_stats.get("created") or 0)
            lead_stats_total["skipped"] += int(lead_stats.get("skipped") or 0)
    db.commit()
    return {
        "ok": True,
        "source": body.source,
        "keyword": body.keyword,
        "location": body.location,
        "runs": flow.get("runs") or [],
        "saved": flow.get("saved_total") or {"created": 0, "updated": 0, "skipped": 0},
        "leads_saved": lead_stats_total,
        "errors": flow.get("errors") or [],
    }


class CompanyEnrichRequest(BaseModel):
    company_ids: List[int] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)
    timeout_seconds: float = Field(default=10.0, ge=2.0, le=30.0)
    delay_seconds: float = Field(default=0.4, ge=0.1, le=5.0)


@router.post("/enrich")
def enrich_companies(
    body: CompanyEnrichRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Step-4 website enrichment:
    - homepage-only safe fetch
    - detect has_blog + has_careers + basic content text
    - skip broken websites gracefully (record fetch_error)
    """
    stats = company_enrichment_service.enrich_companies_batch(
        db,
        company_ids=body.company_ids,
        limit=body.limit,
        timeout_seconds=body.timeout_seconds,
        delay_seconds=body.delay_seconds,
    )
    db.commit()
    return {"ok": True, "stats": stats}


@router.get("/{company_id}/enrichment")
def get_company_enrichment(
    company_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    row = company_enrichment_service.get_company_enrichment(db, company_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Enrichment not found")
    data = company_enrichment_service.enrichment_to_dict(row)
    return data or {}


@router.get("/{domain}", include_in_schema=False)
def get_company_legacy(
    domain: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    # Backward-compatible alias (kept hidden so static endpoints keep priority).
    return get_company(domain=domain, db=db, _user=_user)


class CompanyLeadCandidateRequest(BaseModel):
    min_score: float = Field(default=70.0, ge=0.0, le=100.0)
    limit: int = Field(default=25, ge=1, le=200)
    require_priority: str = Field(default="hot")

    @field_validator("require_priority")
    @classmethod
    def v_pri(cls, v: str) -> str:
        x = (v or "hot").strip().lower()
        if x not in ("hot", "warm", "cold", "any"):
            raise ValueError("require_priority must be hot/warm/cold/any")
        return x


@router.post("/lead-candidates")
def list_company_lead_candidates(
    body: CompanyLeadCandidateRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Step-6: Select high-score companies for manual LinkedIn lead search.
    """
    stmt = (
        select(Company, CompanyEnrichment)
        .join(CompanyEnrichment, CompanyEnrichment.company_id == Company.id)
        .where(CompanyEnrichment.score >= float(body.min_score))
        .order_by(CompanyEnrichment.score.desc(), CompanyEnrichment.last_checked.desc())
        .limit(body.limit)
    )
    rows = []
    for c, e in db.execute(stmt).all():
        pri = str(e.priority or "").strip().lower()
        if body.require_priority != "any" and pri != body.require_priority:
            continue
        rows.append(
            {
                "company_id": c.id,
                "company_name": c.company_name,
                "website": c.website,
                "domain": c.domain,
                "source": c.source,
                "score": float(e.score or 0),
                "priority": e.priority or "",
                "signals": {
                    "hiring": bool(e.signal_hiring),
                    "scaling": bool(e.signal_scaling),
                    "content_gap": bool(e.signal_content_gap),
                    "ads_gap": bool(e.signal_ads_gap),
                },
            }
        )
    return {"count": len(rows), "items": rows}


@router.get("/linkedin/session-check")
def linkedin_session_check(
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Step-6 session handling:
    - check 7-day policy state
    - if stale, client should require manual LinkedIn login before converting company->lead
    """
    info = session_info_dict()
    return {
        **info,
        "requires_manual_login": not bool(info.get("within_policy")),
    }


class CompanyToLeadManualRequest(BaseModel):
    company_id: int = Field(ge=1)
    name: str = Field(min_length=1)
    role: str = ""
    profile_link: str = Field(min_length=1)
    require_fresh_session: bool = True


@router.post("/linkedin/create-lead")
def create_lead_from_company_manual_linkedin(
    body: CompanyToLeadManualRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Company -> Lead conversion (manual LinkedIn flow).

    User does LinkedIn search manually (e.g. \"Founder <Company>\") and submits extracted fields.
    """
    company = db.get(Company, int(body.company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    link = str(body.profile_link or "").strip()
    if "linkedin.com/in/" not in link.lower():
        raise HTTPException(status_code=400, detail="profile_link must be a LinkedIn profile URL (/in/)")

    info = session_info_dict()
    if body.require_fresh_session and not bool(info.get("within_policy")):
        raise HTTPException(
            status_code=409,
            detail="LinkedIn session policy expired; complete manual LinkedIn login first, then retry.",
        )

    lead = lead_orm_service.create_lead(
        db,
        {
            "full_name": str(body.name).strip(),
            "title": str(body.role or "").strip(),
            "company_name": str(company.company_name or "").strip(),
            "company_website": str(company.website or "").strip(),
            "linkedin_url": link,
            "source_platform": "linkedin",
            "notes": f"Created from Company DB (company_id={company.id}) via manual LinkedIn conversion.",
            "user_id": str(user.get("id") or ""),
        },
    )
    db.commit()
    return {
        "ok": True,
        "lead_id": lead.id,
        "company_id": company.id,
        "message": "Lead created from company using manual LinkedIn profile input.",
        "created_by": user.get("id"),
    }


class WeeklyEngineRunRequest(BaseModel):
    day: str = Field(default="", description="mon|tue|wed|thu|fri|sat|sun (empty => detect current day)")
    keyword: str = "software"
    location: str = ""
    batch_size: int = Field(default=10, ge=10, le=20)
    delay_seconds: float = Field(default=1.0, ge=0.2, le=8.0)
    max_companies_per_source: int = Field(default=80, ge=1, le=500)
    enrich_limit: int = Field(default=30, ge=1, le=100)
    enrich_timeout_seconds: float = Field(default=10.0, ge=2.0, le=30.0)
    saturday_min_score: float = Field(default=70.0, ge=0.0, le=100.0)
    saturday_limit: int = Field(default=30, ge=1, le=200)
    saturday_require_fresh_session: bool = True
    saturday_manual_profiles: List[dict[str, Any]] = Field(default_factory=list)


class DailyAutoJobRunRequest(BaseModel):
    keyword: str = "software"
    location: str = ""
    batch_size: int = Field(default=10, ge=10, le=20)
    delay_seconds: float = Field(default=1.0, ge=0.2, le=8.0)
    max_companies_per_source: int = Field(default=80, ge=1, le=500)
    enrich_limit: int = Field(default=20, ge=1, le=100)
    enrich_timeout_seconds: float = Field(default=10.0, ge=2.0, le=30.0)


class ScheduledJobRunRequest(BaseModel):
    job_type: str = Field(description="daily_auto | friday_heavy | saturday_linkedin | sunday_report")
    keyword: str = "software"
    location: str = ""
    batch_size: int = Field(default=10, ge=10, le=20)
    delay_seconds: float = Field(default=1.0, ge=0.2, le=8.0)
    enqueue_only: bool = True

    @field_validator("job_type")
    @classmethod
    def v_job_type(cls, v: str) -> str:
        x = (v or "").strip().lower()
        if x not in company_weekly_engine.SCHEDULED_JOB_TYPES:
            allowed = ", ".join(sorted(company_weekly_engine.SCHEDULED_JOB_TYPES))
            raise ValueError(f"job_type must be one of: {allowed}")
        return x


@router.post("/daily-auto/run")
def run_daily_auto_job(
    body: DailyAutoJobRunRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    STEP W4: Daily auto job pipeline (no login required).
    """
    return company_weekly_engine.run_daily_auto_job(
        db,
        keyword=body.keyword,
        location=body.location,
        batch_size=body.batch_size,
        delay_seconds=body.delay_seconds,
        max_companies_per_source=body.max_companies_per_source,
        enrich_limit=body.enrich_limit,
        enrich_timeout_seconds=body.enrich_timeout_seconds,
    )


@router.post("/scheduler/run")
def run_scheduled_job(
    body: ScheduledJobRunRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    STEP W11 scheduler entry point with explicit job_type dispatch.
    """
    return company_weekly_engine.run_scheduled_job(
        db,
        job_type=body.job_type,
        keyword=body.keyword,
        location=body.location,
        batch_size=body.batch_size,
        delay_seconds=body.delay_seconds,
        enqueue_only=body.enqueue_only,
    )


@router.post("/weekly-engine/run")
def run_weekly_engine(
    body: WeeklyEngineRunRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Step-7 weekly automation engine.

    Mon-Fri: public data ingestion -> enrichment -> scoring
    Saturday: manual LinkedIn expansion prep (session check + candidate queries)
    Sunday: cleanup + reporting
    """
    try:
        return company_weekly_engine.run_weekly_engine(
            db,
            day=body.day,
            keyword=body.keyword,
            location=body.location,
            batch_size=body.batch_size,
            delay_seconds=body.delay_seconds,
            max_companies_per_source=body.max_companies_per_source,
            enrich_limit=body.enrich_limit,
            enrich_timeout_seconds=body.enrich_timeout_seconds,
            saturday_min_score=body.saturday_min_score,
            saturday_limit=body.saturday_limit,
            saturday_manual_profiles=body.saturday_manual_profiles,
            saturday_require_fresh_session=body.saturday_require_fresh_session,
            owner_user_id=str(_user.get("id") or ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
