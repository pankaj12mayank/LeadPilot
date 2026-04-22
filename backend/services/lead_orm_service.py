"""CRUD for SQLAlchemy ``Lead`` rows."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import String, Text, delete, func, or_, select
from sqlalchemy.orm import Session

from database.orm.models import Lead
from backend.services.platform_service import normalize_platform
from backend.services.scoring_service import score
from backend.settings.lead_schema import utc_now_iso


def _score_input_from_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    sp = normalize_platform(str(d.get("source_platform") or d.get("platform") or ""))
    out: Dict[str, Any] = {**d}
    out["full_name"] = str(out.get("full_name") or out.get("name") or "")
    out["source_platform"] = sp
    out["platform"] = sp
    out["company_name"] = str(out.get("company_name") or out.get("company") or "")
    out["company_website"] = str(out.get("company_website") or out.get("website") or "")
    out["linkedin_url"] = str(out.get("linkedin_url") or out.get("profile_url") or "")
    return out


def lead_to_ai_dict(lead: Lead) -> Dict[str, Any]:
    """Map ORM lead to keys expected by ``modules.ai_enricher``."""
    subj_hint = (lead.title or "").strip() or (lead.personalized_message or "")[:80]
    return {
        "name": lead.full_name or "",
        "platform": lead.source_platform or "",
        "company": lead.company_name or "",
        "notes": lead.notes or "",
        "email": lead.email or "",
        "subject": subj_hint,
    }


def lead_to_response_dict(lead: Lead) -> Dict[str, Any]:
    return {
        "id": lead.id,
        "full_name": lead.full_name,
        "title": lead.title,
        "company_name": lead.company_name,
        "company_website": lead.company_website,
        "linkedin_url": lead.linkedin_url,
        "email": lead.email,
        "phone": lead.phone,
        "company_size": lead.company_size,
        "industry": lead.industry,
        "location": lead.location,
        "source_platform": lead.source_platform,
        "notes": lead.notes,
        "score": lead.score,
        "tier": lead.tier,
        "status": lead.status,
        "personalized_message": lead.personalized_message,
        "followup_message": lead.followup_message,
        "last_contacted_at": getattr(lead, "last_contacted_at", "") or "",
        "follow_up_reminder_at": getattr(lead, "follow_up_reminder_at", "") or "",
        "created_at": lead.created_at,
        "updated_at": lead.updated_at,
    }


def _apply_list_filters(
    stmt,
    *,
    search: Optional[str],
    status: Optional[str],
    tier: Optional[str],
    platform: Optional[str],
):
    if search and str(search).strip():
        term = f"%{str(search).strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Lead.full_name).like(term),
                func.lower(Lead.email).like(term),
                func.lower(Lead.company_name).like(term),
                func.lower(Lead.title).like(term),
                func.lower(Lead.source_platform).like(term),
            )
        )
    if status and str(status).strip():
        stmt = stmt.where(func.lower(Lead.status) == str(status).strip().lower())
    if tier and str(tier).strip():
        stmt = stmt.where(func.lower(Lead.tier) == str(tier).strip().lower())
    if platform and str(platform).strip():
        stmt = stmt.where(Lead.source_platform == normalize_platform(str(platform).strip()))
    return stmt


def count_leads_filtered(
    db: Session,
    *,
    search: Optional[str] = None,
    status: Optional[str] = None,
    tier: Optional[str] = None,
    platform: Optional[str] = None,
) -> int:
    stmt = select(func.count(Lead.id))
    stmt = _apply_list_filters(stmt, search=search, status=status, tier=tier, platform=platform)
    return int(db.scalar(stmt) or 0)


def list_leads_filtered(
    db: Session,
    *,
    search: Optional[str] = None,
    status: Optional[str] = None,
    tier: Optional[str] = None,
    platform: Optional[str] = None,
    sort: str = "created_at_desc",
    offset: int = 0,
    limit: int = 25,
) -> List[Lead]:
    stmt = select(Lead)
    stmt = _apply_list_filters(stmt, search=search, status=status, tier=tier, platform=platform)
    if sort == "created_at_asc":
        stmt = stmt.order_by(Lead.created_at.asc())
    elif sort == "score_desc":
        stmt = stmt.order_by(Lead.score.desc(), Lead.created_at.desc())
    elif sort == "name_asc":
        stmt = stmt.order_by(Lead.full_name.asc())
    else:
        stmt = stmt.order_by(Lead.created_at.desc())
    stmt = stmt.offset(max(0, offset)).limit(min(200, max(1, limit)))
    return list(db.scalars(stmt))


def list_leads(db: Session) -> List[Lead]:
    return list(db.scalars(select(Lead).order_by(Lead.created_at.desc())))


def get_lead(db: Session, lead_id: str) -> Optional[Lead]:
    return db.get(Lead, lead_id)


def _norm_profile_url(url: str) -> str:
    s = (url or "").strip().rstrip("/")
    return s.lower() if s else ""


def ingest_scrape_rows_into_leads(
    db: Session,
    *,
    platform: str,
    rows: List[Dict[str, Any]],
) -> Dict[str, int]:
    """
    Insert scraper output into the main ``leads`` table so the CRM list updates.

    Skips rows without a usable LinkedIn profile URL and skips duplicates
    (same profile URL as an existing lead, case-insensitive).
    """
    plat = normalize_platform(platform)
    created = 0
    skipped = 0
    for r in rows:
        linkedin = str(r.get("linkedin_url") or r.get("url") or "").strip()
        if not linkedin or "/in/" not in linkedin.lower():
            skipped += 1
            continue
        key = _norm_profile_url(linkedin)
        if not key:
            skipped += 1
            continue
        dup = db.scalar(
            select(Lead.id).where(func.lower(func.trim(Lead.linkedin_url)) == key).limit(1)
        )
        if dup is not None:
            skipped += 1
            continue
        full_name = (str(r.get("full_name") or "").strip() or "Unknown")[:255]
        kw = str(r.get("search_keyword") or "").strip()
        fc = str(r.get("filter_country") or "").strip()
        fi = str(r.get("filter_industry") or "").strip()
        fcs = str(r.get("filter_company_size") or "").strip()
        notes_parts: List[str] = []
        if kw:
            notes_parts.append(f"Search: {kw}")
        if fc:
            notes_parts.append(f"Location / region: {fc}")
        if fi:
            notes_parts.append(f"Industry filter: {fi}")
        if fcs:
            notes_parts.append(f"Company size filter: {fcs}")
        note_body = "\n".join(notes_parts)[:7900]
        em = str(r.get("email") or "").strip()[:320]
        ph = str(r.get("phone") or "").strip()[:64]
        payload: Dict[str, Any] = {
            "full_name": full_name,
            "source_platform": plat,
            "title": (str(r.get("title") or ""))[:4000],
            "company_name": (str(r.get("company_name") or ""))[:4000],
            "linkedin_url": linkedin[:4000],
            "industry": (fi or str(r.get("industry") or ""))[:128],
            "company_size": (fcs or str(r.get("company_size") or ""))[:64],
            "location": fc[:255] if fc else (str(r.get("location") or "")[:255]),
            "email": em,
            "phone": ph,
            "notes": note_body,
        }
        create_lead(db, payload)
        created += 1
    return {"ingested_leads": created, "skipped": skipped}


def create_lead(db: Session, data: Dict[str, Any]) -> Lead:
    lid = str(uuid.uuid4())
    now = utc_now_iso()
    row = {**data}
    row["source_platform"] = normalize_platform(str(row.get("source_platform") or ""))
    sc = score(_score_input_from_dict(row))
    lead = Lead(
        id=lid,
        full_name=str(row.get("full_name") or "").strip(),
        title=str(row.get("title") or ""),
        company_name=str(row.get("company_name") or ""),
        company_website=str(row.get("company_website") or ""),
        linkedin_url=str(row.get("linkedin_url") or ""),
        email=str(row.get("email") or ""),
        phone=str(row.get("phone") or ""),
        company_size=str(row.get("company_size") or ""),
        industry=str(row.get("industry") or ""),
        location=str(row.get("location") or ""),
        source_platform=str(row.get("source_platform") or ""),
        notes=str(row.get("notes") or ""),
        score=float(sc.get("score") or 0),
        tier=str(sc.get("tier") or ""),
        status=str(row.get("status") or "new") or "new",
        personalized_message=str(row.get("personalized_message") or ""),
        followup_message=str(row.get("followup_message") or ""),
        last_contacted_at=str(row.get("last_contacted_at") or ""),
        follow_up_reminder_at=str(row.get("follow_up_reminder_at") or ""),
        created_at=now,
        updated_at=now,
    )
    db.add(lead)
    db.flush()
    db.refresh(lead)
    return lead


def update_lead(db: Session, lead_id: str, patch: Dict[str, Any]) -> Optional[Lead]:
    lead = db.get(Lead, lead_id)
    if not lead:
        return None
    now = utc_now_iso()
    col_keys = {c.key for c in Lead.__table__.columns}
    for k, v in patch.items():
        if k not in col_keys or k in ("id", "created_at"):
            continue
        col = Lead.__table__.columns[k]
        if v is None:
            if isinstance(col.type, (String, Text)):
                setattr(lead, k, "")
            continue
        setattr(lead, k, v)
    if any(
        k in patch
        for k in (
            "full_name",
            "title",
            "source_platform",
            "company_name",
            "company_size",
            "industry",
            "location",
            "country",
            "email",
            "notes",
            "linkedin_url",
            "company_website",
        )
    ):
        d = lead_to_response_dict(lead)
        sc = score(_score_input_from_dict(d))
        lead.score = float(sc.get("score") or 0)
        lead.tier = str(sc.get("tier") or "")
    lead.updated_at = now
    db.flush()
    db.refresh(lead)
    return lead


def update_status(db: Session, lead_id: str, status: str) -> Optional[Lead]:
    return update_lead(db, lead_id, {"status": status})


def delete_lead(db: Session, lead_id: str) -> bool:
    lead = db.get(Lead, lead_id)
    if not lead:
        return False
    db.delete(lead)
    db.flush()
    return True


def bulk_delete_leads(db: Session, lead_ids: List[str]) -> int:
    if not lead_ids:
        return 0
    clean = [str(x).strip() for x in lead_ids if str(x).strip()]
    if not clean:
        return 0
    res = db.execute(delete(Lead).where(Lead.id.in_(clean)))
    db.flush()
    return int(res.rowcount or 0)


def fetch_leads_by_ids(db: Session, lead_ids: List[str]) -> List[Lead]:
    if not lead_ids:
        return []
    clean = [str(x).strip() for x in lead_ids if str(x).strip()]
    if not clean:
        return []
    return list(db.scalars(select(Lead).where(Lead.id.in_(clean))))


def list_leads_for_export(
    db: Session,
    *,
    ids: Optional[List[str]] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    tier: Optional[str] = None,
    platform: Optional[str] = None,
) -> List[Lead]:
    if ids:
        rows = fetch_leads_by_ids(db, ids)
        return sorted(rows, key=lambda x: x.created_at or "", reverse=True)
    return list_leads_filtered(
        db,
        search=search,
        status=status,
        tier=tier,
        platform=platform,
        sort="created_at_desc",
        offset=0,
        limit=50_000,
    )
