"""Company table helpers: normalize domain, upsert by domain, fetch, and ingest mock/public rows."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.settings.lead_schema import utc_now_iso
from database.orm.models import Company

ALLOWED_COMPANY_SOURCES = frozenset({"job_board", "yc", "local", "manual", "crunchbase", "builtwith"})


def normalize_company_domain(value: str | None) -> str:
    """
    Normalize a company website/domain into a dedupe key.

    Examples:
    - ``https://www.Acme.com/about`` -> ``acme.com``
    - ``WWW.ACME.COM`` -> ``acme.com``
    - ``acme.com/path`` -> ``acme.com``
    """
    raw = (value or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw.lstrip("/")
    try:
        p = urlparse(raw)
    except Exception:
        return ""
    host = (p.netloc or p.path or "").strip().lower()
    if "@" in host:
        host = host.split("@", 1)[-1]
    if ":" in host:
        host = host.split(":", 1)[0]
    while host.startswith("www."):
        host = host[4:]
    host = host.strip(". /")
    if "." not in host or " " in host:
        return ""
    return host


def normalize_company_source(value: str | None) -> str:
    """
    Normalize source into canonical set required by Step-1.

    Unknown/empty values fall back to ``manual``.
    """
    s = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if s in ALLOWED_COMPANY_SOURCES:
        return s
    if s:
        try:
            from backend.services import runtime_settings

            if runtime_settings.get_source_registry_entry(s) is not None:
                return s
        except Exception:
            pass
    return "manual"


def get_company_by_domain(db: Session, domain: str | None) -> Optional[Company]:
    dom = normalize_company_domain(domain)
    if not dom:
        return None
    stmt = select(Company).where(func.lower(Company.domain) == dom).limit(1)
    return db.scalar(stmt)


def _merge_sources(current: str | None, incoming: str | None) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for raw in [*(str(current or "").split(",")), *(str(incoming or "").split(","))]:
        src = normalize_company_source(raw.strip())
        if src and src not in seen:
            seen.add(src)
            values.append(src)
    return ",".join(values)


def _normalize_signals(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        active = [str(k).strip() for k, v in value.items() if bool(v)]
        return ",".join(active)
    if isinstance(value, list):
        return ",".join(str(x).strip() for x in value if str(x).strip())
    return ""


def _parse_iso_dt(value: str | None) -> datetime | None:
    s = str(value or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def list_companies(db: Session) -> list[Company]:
    return list(db.scalars(select(Company).order_by(Company.last_updated.desc(), Company.id.desc())))


def list_companies_filtered(
    db: Session,
    *,
    source_filter: str = "all",
    updated_within_days: int = 0,
    limit: int = 500,
) -> list[Company]:
    stmt = select(Company)
    src = str(source_filter or "all").strip().lower()
    if src and src != "all":
        stmt = stmt.where(func.lower(Company.source).like(f"%{src}%"))
    if int(updated_within_days or 0) > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(updated_within_days))
        stmt = stmt.where(Company.last_updated >= cutoff.replace(microsecond=0).isoformat())
    stmt = stmt.order_by(Company.last_updated.desc(), Company.id.desc()).limit(max(1, min(int(limit or 500), 1000)))
    return list(db.scalars(stmt))


def search_companies(
    db: Session,
    *,
    keyword: str,
    location: str = "",
    source_filter: str = "all",
    updated_within_days: int | None = None,
    limit: int = 50,
) -> list[Company]:
    """
    Explorer query against company DB.

    Matching rule: ``company_name`` OR ``domain`` OR ``website`` contains the keyword.
    ``location`` is optional; currently treated as a soft token (applied only if present in same fields).
    """
    kw = str(keyword or "").strip().lower()
    if not kw:
        return []
    lim = max(1, min(int(limit or 50), 500))
    term = f"%{kw}%"
    stmt = select(Company).where(
        func.lower(Company.company_name).like(term)
        | func.lower(Company.domain).like(term)
        | func.lower(Company.website).like(term)
    )
    loc = str(location or "").strip().lower()
    if loc:
        loc_term = f"%{loc}%"
        stmt = stmt.where(
            func.lower(Company.company_name).like(loc_term)
            | func.lower(Company.domain).like(loc_term)
            | func.lower(Company.website).like(loc_term)
        )
    src = str(source_filter or "all").strip().lower()
    if src and src != "all":
        stmt = stmt.where(func.lower(Company.source).like(f"%{src}%"))
    if updated_within_days is not None and int(updated_within_days) > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(updated_within_days))
        stmt = stmt.where(Company.last_updated >= cutoff.replace(microsecond=0).isoformat())
    stmt = stmt.order_by(Company.last_updated.desc(), Company.id.desc()).limit(lim)
    return list(db.scalars(stmt))


def company_to_dict(row: Company) -> dict[str, Any]:
    return {
        "id": row.id,
        "company_name": row.company_name,
        "website": row.website,
        "domain": row.domain,
        "source": row.source,
        "source_values": [x for x in str(row.source or "").split(",") if x],
        "signals": [x for x in str(getattr(row, "signals", "") or "").split(",") if x],
        "ai_score": float(getattr(row, "ai_score", 0.0) or 0.0),
        "first_seen": row.first_seen,
        "last_updated": row.last_updated,
    }


def create_company(
    db: Session,
    *,
    company_name: str,
    website: str,
    source: str = "",
    signals: Any = None,
    ai_score: float = 0.0,
) -> Company:
    dom = normalize_company_domain(website)
    if not dom:
        raise ValueError("A valid website/domain is required to create a company")
    src = normalize_company_source(source)
    now = utc_now_iso()
    row = Company(
        company_name=str(company_name or "").strip(),
        website=str(website or "").strip(),
        domain=dom,
        source=src,
        signals=_normalize_signals(signals),
        ai_score=float(ai_score or 0.0),
        first_seen=now,
        last_updated=now,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def upsert_company(
    db: Session,
    *,
    company_name: str,
    website: str,
    source: str = "",
    signals: Any = None,
    ai_score: float = 0.0,
) -> Company:
    """
    Insert or update a company, deduping strictly by normalized domain.

    Existing rows keep ``first_seen`` and get refreshed ``last_updated``.
    Empty new values never overwrite non-empty existing values.
    """
    dom = normalize_company_domain(website)
    if not dom:
        raise ValueError("A valid website/domain is required to upsert a company")
    src = normalize_company_source(source)
    now = utc_now_iso()
    row = get_company_by_domain(db, dom)
    if row is None:
        return create_company(
            db,
            company_name=company_name,
            website=website,
            source=src,
            signals=signals,
            ai_score=ai_score,
        )
    new_name = str(company_name or "").strip()
    new_site = str(website or "").strip()
    new_source = src
    if new_name:
        row.company_name = new_name
    if new_site:
        row.website = new_site
    if new_source:
        row.source = _merge_sources(row.source, new_source)
    normalized_signals = _normalize_signals(signals)
    if normalized_signals:
        row.signals = normalized_signals
    row.ai_score = max(float(ai_score or 0.0), float(getattr(row, "ai_score", 0.0) or 0.0))
    row.domain = dom
    row.last_updated = now
    db.flush()
    db.refresh(row)
    return row


def ingest_public_companies(
    db: Session,
    rows: list[dict[str, Any]],
    *,
    default_source: str = "manual",
) -> dict[str, int]:
    """
    Populate the company DB from a simple manual/mock list.

    Accepted keys per row:
    - ``company_name`` or ``name``
    - ``website`` or ``domain``
    - optional ``source``
    """
    created = 0
    updated = 0
    skipped = 0
    for raw in rows:
        company_name = str(raw.get("company_name") or raw.get("name") or "").strip()
        website_or_domain = str(raw.get("website") or raw.get("domain") or "").strip()
        source = normalize_company_source(str(raw.get("source") or default_source or "").strip())
        signals = raw.get("signals")
        ai_score = float(raw.get("ai_score") or 0.0)
        dom = normalize_company_domain(website_or_domain)
        if not company_name or not dom:
            skipped += 1
            continue
        existing = get_company_by_domain(db, dom)
        upsert_company(
            db,
            company_name=company_name,
            website=website_or_domain,
            source=source,
            signals=signals,
            ai_score=ai_score,
        )
        if existing is None:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated, "skipped": skipped}


def list_stale_companies(db: Session, *, stale_days: int = 7, limit: int = 200) -> list[Company]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(stale_days or 7)))
    stmt = (
        select(Company)
        .where(Company.last_updated <= cutoff.replace(microsecond=0).isoformat())
        .order_by(Company.last_updated.asc(), Company.id.asc())
        .limit(max(1, min(int(limit or 200), 1000)))
    )
    return list(db.scalars(stmt))
