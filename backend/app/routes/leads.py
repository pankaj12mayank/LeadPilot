from __future__ import annotations

import csv
import io
import math
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.schemas.lead import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    BulkImportRequest,
    BulkImportResponse,
    LeadCreate,
    LeadExportRequest,
    LeadResponse,
    LeadUpdate,
    PaginatedLeadsResponse,
    StatusUpdate,
)
from backend.services import (
    analytics_service,
    email_history_service,
    history_service,
    lead_orm_service,
    status_history_service,
)


def _invalidate_dashboard_cache() -> None:
    try:
        analytics_service.invalidate_analytics_cache()
    except Exception:
        pass
from backend.services.platform_service import normalize_platform

router = APIRouter(prefix="/leads", tags=["leads"])

_CSV_FIELDS = [
    "id",
    "full_name",
    "title",
    "company_name",
    "company_website",
    "linkedin_url",
    "email",
    "phone",
    "company_size",
    "industry",
    "location",
    "source_platform",
    "notes",
    "score",
    "tier",
    "status",
    "personalized_message",
    "followup_message",
    "last_contacted_at",
    "follow_up_reminder_at",
    "created_at",
    "updated_at",
    "agency_type",
    "problem_seen",
    "last_active_display",
    "connection_sent",
    "replied_yn",
    "solution_text",
    "signal_hiring",
    "signal_scaling",
    "signal_content_gap",
    "signal_ads_gap",
    "priority",
]


def _create_from_body(db: Session, body: LeadCreate, user_id: str) -> LeadResponse:
    stored = lead_orm_service.create_lead(db, body.model_dump(exclude_none=True))
    db.commit()
    history_service.record_event(
        stored.id,
        "lead.created",
        {"full_name": stored.full_name},
        user_id,
    )
    _invalidate_dashboard_cache()
    return LeadResponse.from_orm_lead(stored)


def _csv_cell_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    if s.lower() in ("nan", "none", "<na>"):
        return ""
    return s


def _csv_cell_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    s = str(v).strip() if v is not None else ""
    if not s or s.lower() in ("nan", "none", "<na>"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _csv_row_to_lead_dict(r: Dict[str, Any]) -> Dict[str, Any] | None:
    """Map one CSV row (lowercase keys) to ``LeadCreate`` fields; aligned with :data:`_CSV_FIELDS` / export."""
    full_name = _csv_cell_str(r.get("full_name") or r.get("name", ""))
    source_platform = normalize_platform(_csv_cell_str(r.get("source_platform") or r.get("platform", "")))
    linkedin_url = _csv_cell_str(
        r.get("linkedin_url") or r.get("profile_url", "") or r.get("url", "")
    )
    company_website = _csv_cell_str(r.get("company_website") or r.get("website", ""))
    email = _csv_cell_str(r.get("email", ""))
    if not full_name or not source_platform:
        return None
    if not (linkedin_url or company_website or email):
        return None

    out: Dict[str, Any] = {
        "full_name": full_name,
        "source_platform": source_platform,
        "title": _csv_cell_str(r.get("title", "")),
        "company_name": _csv_cell_str(r.get("company_name") or r.get("company", "")),
        "company_website": company_website,
        "linkedin_url": linkedin_url,
        "email": email,
        "phone": _csv_cell_str(r.get("phone", "")),
        "company_size": _csv_cell_str(r.get("company_size", "")),
        "industry": _csv_cell_str(r.get("industry", "")),
        "location": _csv_cell_str(r.get("location", "")),
        "notes": _csv_cell_str(r.get("notes", "")),
        "status": _csv_cell_str(r.get("status", "")) or "new",
        "personalized_message": _csv_cell_str(r.get("personalized_message", "")),
        "followup_message": _csv_cell_str(r.get("followup_message", "")),
        "last_contacted_at": _csv_cell_str(r.get("last_contacted_at", "")),
        "follow_up_reminder_at": _csv_cell_str(r.get("follow_up_reminder_at", "")),
        "agency_type": _csv_cell_str(r.get("agency_type", "")),
        "problem_seen": _csv_cell_str(r.get("problem_seen", "")),
        "last_active_display": _csv_cell_str(r.get("last_active_display", "")),
        "connection_sent": _csv_cell_str(r.get("connection_sent", "")),
        "replied_yn": _csv_cell_str(r.get("replied_yn", "")) or "N",
        "solution_text": _csv_cell_str(r.get("solution_text", "")),
        "signal_hiring": 1 if _csv_cell_str(r.get("signal_hiring", "")).lower() in ("1", "true", "yes", "y") else 0,
        "signal_scaling": 1 if _csv_cell_str(r.get("signal_scaling", "")).lower() in ("1", "true", "yes", "y") else 0,
        "signal_content_gap": 1
        if _csv_cell_str(r.get("signal_content_gap", "")).lower() in ("1", "true", "yes", "y")
        else 0,
        "signal_ads_gap": 1 if _csv_cell_str(r.get("signal_ads_gap", "")).lower() in ("1", "true", "yes", "y") else 0,
        "priority": _csv_cell_str(r.get("priority", "")),
    }
    fs = _csv_cell_float(r.get("score"))
    if fs is not None:
        out["score"] = max(0.0, min(100.0, fs))
    tt = _csv_cell_str(r.get("tier", ""))
    if tt:
        out["tier"] = tt
    return out


def _leads_template_csv_bytes() -> bytes:
    """Header row + one sample line (same columns as :meth:`export_leads_csv`)."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    sample: Dict[str, str] = {k: "" for k in _CSV_FIELDS}
    sample.update(
        {
            "id": "",
            "full_name": "Sample Contact",
            "title": "Head of Marketing",
            "company_name": "Acme Co",
            "company_website": "https://acme.example.com",
            "linkedin_url": "https://www.linkedin.com/in/sample-profile",
            "email": "sample@acme.example.com",
            "phone": "",
            "company_size": "11-50",
            "industry": "SaaS",
            "location": "Remote",
            "source_platform": "linkedin",
            "notes": "Delete this row or replace with your data. Export from Leads reuses the same columns.",
            "score": "",
            "tier": "",
            "status": "new",
            "personalized_message": "",
            "followup_message": "",
            "last_contacted_at": "",
            "follow_up_reminder_at": "",
            "created_at": "",
            "updated_at": "",
            "agency_type": "",
            "problem_seen": "",
            "last_active_display": "",
            "connection_sent": "",
            "replied_yn": "N",
            "solution_text": "",
            "signal_hiring": "",
            "signal_scaling": "",
            "signal_content_gap": "",
            "signal_ads_gap": "",
            "priority": "",
        }
    )
    writer.writerow(sample)
    return buf.getvalue().encode("utf-8")


def _leads_to_csv_bytes(leads: List[Any]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in leads:
        writer.writerow(LeadResponse.from_orm_lead(row).model_dump())
    return buf.getvalue().encode("utf-8")


def _list_leads_paginated_core(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    status: str | None,
    tier: str | None,
    platform: str | None,
    sort: str,
) -> PaginatedLeadsResponse:
    total = lead_orm_service.count_leads_filtered(
        db, search=search, status=status, tier=tier, platform=platform
    )
    offset = (page - 1) * page_size
    rows = lead_orm_service.list_leads_filtered(
        db,
        search=search,
        status=status,
        tier=tier,
        platform=platform,
        sort=sort,
        offset=offset,
        limit=page_size,
    )
    pages = (total + page_size - 1) // page_size if page_size else 0
    return PaginatedLeadsResponse(
        items=[LeadResponse.from_orm_lead(x) for x in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("", response_model=PaginatedLeadsResponse)
@router.get("/", response_model=PaginatedLeadsResponse, include_in_schema=False)
def list_leads(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    search: str | None = Query(None),
    status: str | None = Query(None),
    tier: str | None = Query(None),
    platform: str | None = Query(None),
    sort: str = Query(
        "created_at_desc",
        description="created_at_desc | created_at_asc | score_desc | name_asc",
    ),
) -> PaginatedLeadsResponse:
    """Paginated lead list with optional search and filters (GET /leads)."""
    return _list_leads_paginated_core(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        tier=tier,
        platform=platform,
        sort=sort,
    )


@router.post("", response_model=LeadResponse)
@router.post("/", response_model=LeadResponse, include_in_schema=False)
def create_lead(
    body: LeadCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> LeadResponse:
    """Create a lead (POST /leads)."""
    return _create_from_body(db, body, user["id"])


@router.post("/export")
def export_leads_csv(
    body: LeadExportRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> Response:
    """Export leads as UTF-8 CSV (optional id list or same filters as list)."""
    leads = lead_orm_service.list_leads_for_export(
        db,
        ids=body.ids,
        search=body.search,
        status=body.status,
        tier=body.tier,
        platform=body.platform,
    )
    db.commit()
    history_service.record_event(
        None,
        "leads.export",
        {"rows": len(leads), "filtered": body.ids is None},
        user["id"],
    )
    return Response(
        content=_leads_to_csv_bytes(leads),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="leads_export.csv"'},
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_leads(
    body: BulkDeleteRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> BulkDeleteResponse:
    n = lead_orm_service.bulk_delete_leads(db, body.ids)
    db.commit()
    history_service.record_event(
        None,
        "leads.bulk_deleted",
        {"count": n, "sample_ids": body.ids[:20]},
        user["id"],
    )
    _invalidate_dashboard_cache()
    return BulkDeleteResponse(deleted=n)


@router.post("/bulk-import", response_model=BulkImportResponse)
async def bulk_import(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> BulkImportResponse:
    created = 0
    errors: List[str] = []
    ct = request.headers.get("content-type", "")
    rows: List[Dict[str, Any]] = []

    if "multipart/form-data" in ct:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(
                status_code=400,
                detail="Multipart bulk import requires form field 'file' (CSV).",
            )
        raw = await upload.read()  # type: ignore[union-attr]
        try:
            df = pd.read_csv(io.BytesIO(raw))
            df.columns = [str(c).strip().lower() for c in df.columns]
            for _, r in df.iterrows():
                row_dict = {str(k).lower(): v for k, v in r.items()}
                payload = _csv_row_to_lead_dict(row_dict)
                if payload:
                    rows.append(payload)
                else:
                    errors.append("Skipped row (need full_name + source_platform + linkedin_url or company_website or email)")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}") from e
    else:
        try:
            data = await request.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail="Expected JSON or multipart CSV") from e
        req = BulkImportRequest.model_validate(data)
        for item in req.leads:
            rows.append(item.model_dump(exclude_none=True))

    for i, raw_lead in enumerate(rows):
        try:
            body = LeadCreate.model_validate(raw_lead)
            _create_from_body(db, body, user["id"])
            created += 1
        except Exception as e:
            errors.append(f"Row {i}: {e}")

    history_service.record_event(
        None,
        "leads.bulk_import",
        {"created": created, "errors": len(errors)},
        user["id"],
    )
    if created:
        _invalidate_dashboard_cache()
    return BulkImportResponse(created=created, errors=errors)


@router.get("/csv-template")
def download_leads_csv_template(
    _user: dict = Depends(get_current_user),
) -> Response:
    """Download a CSV with the same headers as :meth:`export_leads_csv` and one example row (for import)."""
    return Response(
        content=_leads_template_csv_bytes(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="leads_import_template.csv"'},
    )


@router.post("/add", response_model=LeadResponse)
def add_lead(
    body: LeadCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> LeadResponse:
    """Legacy alias for POST /leads."""
    return _create_from_body(db, body, user["id"])


@router.get("/{lead_id}/history")
def lead_history(
    lead_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    if not lead_orm_service.get_lead(db, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    return history_service.list_for_lead(lead_id)


@router.get("/{lead_id}/status-history")
def lead_status_history(
    lead_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    if not lead_orm_service.get_lead(db, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    return status_history_service.list_for_lead(lead_id)


@router.get("/{lead_id}/email-history")
def lead_email_history(
    lead_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    if not lead_orm_service.get_lead(db, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    return email_history_service.list_for_lead(lead_id)


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> LeadResponse:
    row = lead_orm_service.get_lead(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.from_orm_lead(row)


@router.put("/{lead_id}", response_model=LeadResponse)
def put_lead(
    lead_id: str,
    body: LeadUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> LeadResponse:
    """Full/partial update (PUT /leads/{id}); same merge semantics as PATCH."""
    patch = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if "source_platform" in patch and patch["source_platform"] is not None:
        patch["source_platform"] = normalize_platform(str(patch["source_platform"]))
    row = lead_orm_service.update_lead(db, lead_id, patch)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.commit()
    history_service.record_event(lead_id, "lead.updated", {"fields": list(patch.keys())}, user["id"])
    _invalidate_dashboard_cache()
    return LeadResponse.from_orm_lead(row)


@router.patch("/{lead_id}", response_model=LeadResponse)
def patch_lead(
    lead_id: str,
    body: LeadUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> LeadResponse:
    patch = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if "source_platform" in patch and patch["source_platform"] is not None:
        patch["source_platform"] = normalize_platform(str(patch["source_platform"]))
    row = lead_orm_service.update_lead(db, lead_id, patch)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.commit()
    history_service.record_event(lead_id, "lead.updated", {"fields": list(patch.keys())}, user["id"])
    _invalidate_dashboard_cache()
    return LeadResponse.from_orm_lead(row)


@router.delete("/{lead_id}")
def remove_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    ok = lead_orm_service.delete_lead(db, lead_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.commit()
    history_service.record_event(lead_id, "lead.deleted", None, user["id"])
    _invalidate_dashboard_cache()
    return {"deleted": True}


@router.patch("/{lead_id}/status", response_model=LeadResponse)
def patch_status(
    lead_id: str,
    body: StatusUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> LeadResponse:
    prev_row = lead_orm_service.get_lead(db, lead_id)
    if not prev_row:
        raise HTTPException(status_code=404, detail="Lead not found")
    old_status = str(prev_row.status or "")
    row = lead_orm_service.update_status(db, lead_id, body.status)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.commit()
    if old_status != body.status:
        status_history_service.record_change(lead_id, old_status, body.status)
    history_service.record_event(
        lead_id,
        "lead.status_changed",
        {"status": body.status},
        user["id"],
    )
    _invalidate_dashboard_cache()
    return LeadResponse.from_orm_lead(row)
