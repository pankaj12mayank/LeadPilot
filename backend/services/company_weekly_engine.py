"""Weekly automation engine for company growth + manual LinkedIn expansion prep."""

from __future__ import annotations

import time
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.leadpilot.linkedin_session_cache import session_info_dict
from backend.services import company_enrichment_service, company_ingestion_service, company_service
from backend.utils.logger import get_logger
from database.orm.models import Company, CompanyEnrichment

logger = get_logger(__name__)

WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _retry_call(
    fn: Callable[[], Any],
    *,
    attempts: int = 3,
    base_delay: float = 0.8,
    label: str = "task",
) -> Any:
    last_err: Exception | None = None
    for i in range(1, max(1, attempts) + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("weekly_engine retry %s/%s for %s: %s", i, attempts, label, e)
            if i < attempts:
                time.sleep(base_delay * i)
    assert last_err is not None
    raise last_err


def _normalize_day(day: str) -> str:
    d = (day or "").strip().lower()[:3]
    if d not in WEEKDAY_KEYS:
        raise ValueError(f"Invalid day {day!r}; expected one of: {', '.join(WEEKDAY_KEYS)}")
    return d


def _source_plan_for_weekday(day: str) -> list[str]:
    # Keep source fanout moderate to avoid aggressive traffic.
    return ["yc", "job_board", "local", "crunchbase", "builtwith"]


def _run_mon_to_fri(
    db: Session,
    *,
    keyword: str,
    location: str,
    batch_size: int,
    delay_seconds: float,
    max_companies_per_source: int,
    enrich_limit: int,
    enrich_timeout_seconds: float,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    saved_total = {"created": 0, "updated": 0, "skipped": 0}
    for src in _source_plan_for_weekday("mon"):
        seeds = company_ingestion_service.default_seed_urls_for_source(source=src, keyword=keyword, location=location)
        if not seeds:
            continue
        candidates, fetched = _retry_call(
            lambda: company_ingestion_service.collect_companies_from_source_pages(
                source=src,
                seed_urls=seeds,
                batch_size=batch_size,
                delay_seconds=delay_seconds,
                max_companies=max_companies_per_source,
            ),
            label=f"ingest-{src}",
        )
        saved = company_service.ingest_public_companies(db, candidates, default_source=src)
        saved_total["created"] += int(saved.get("created") or 0)
        saved_total["updated"] += int(saved.get("updated") or 0)
        saved_total["skipped"] += int(saved.get("skipped") or 0)
        runs.append({"source": src, "fetched": fetched, "saved": saved})
    enrich_stats = _retry_call(
        lambda: company_enrichment_service.enrich_companies_batch(
            db,
            limit=enrich_limit,
            timeout_seconds=enrich_timeout_seconds,
            delay_seconds=min(2.0, delay_seconds),
        ),
        label="enrich",
    )
    db.commit()
    logger.info("weekly_engine mon-fri done: saved=%s enrich=%s", saved_total, enrich_stats)
    return {"runs": runs, "saved_total": saved_total, "enrichment": enrich_stats}


def _run_saturday(db: Session, *, min_score: float, limit: int) -> dict[str, Any]:
    # Manual LinkedIn day: no auto login, no auto profile extraction.
    sess = session_info_dict()
    stmt = (
        select(Company, CompanyEnrichment)
        .join(CompanyEnrichment, CompanyEnrichment.company_id == Company.id)
        .where(CompanyEnrichment.score >= float(min_score))
        .order_by(CompanyEnrichment.score.desc(), CompanyEnrichment.last_checked.desc())
        .limit(max(1, min(limit, 200)))
    )
    candidates = []
    for c, e in db.execute(stmt).all():
        candidates.append(
            {
                "company_id": c.id,
                "company_name": c.company_name,
                "website": c.website,
                "score": float(e.score or 0),
                "priority": e.priority or "",
                "linkedin_manual_query": f"Founder {c.company_name}",
            }
        )
    logger.info("weekly_engine saturday prepared candidates=%s", len(candidates))
    return {
        "session": sess,
        "requires_manual_login": bool(sess.get("has_cache")) and not bool(sess.get("within_policy")),
        "instructions": "Open LinkedIn manually, search each query, and use /companies/linkedin/create-lead.",
        "candidates": candidates,
    }


def _run_sunday(db: Session) -> dict[str, Any]:
    # Lightweight cleanup + reporting (non-destructive to leads).
    trimmed = 0
    for e in db.scalars(select(CompanyEnrichment)):
        txt = str(e.content_text or "")
        if len(txt) > 4000:
            e.content_text = txt[:4000]
            trimmed += 1
    report = {
        "companies_total": int(db.scalar(select(func.count(Company.id))) or 0),
        "enriched_total": int(db.scalar(select(func.count(CompanyEnrichment.id))) or 0),
        "high_priority_companies": int(
            db.scalar(select(func.count(CompanyEnrichment.id)).where(func.lower(CompanyEnrichment.priority) == "hot"))
            or 0
        ),
        "trimmed_content_rows": trimmed,
    }
    db.commit()
    logger.info("weekly_engine sunday cleanup/report: %s", report)
    return report


def run_weekly_engine(
    db: Session,
    *,
    day: str,
    keyword: str = "software",
    location: str = "",
    batch_size: int = 10,
    delay_seconds: float = 1.0,
    max_companies_per_source: int = 80,
    enrich_limit: int = 30,
    enrich_timeout_seconds: float = 10.0,
    saturday_min_score: float = 70.0,
    saturday_limit: int = 30,
) -> dict[str, Any]:
    """
    Weekly automation orchestrator.

    Mon-Fri: ingestion -> enrichment -> scoring
    Saturday: manual LinkedIn expansion prep (session check + candidate list)
    Sunday: cleanup + reporting
    """
    d = _normalize_day(day)
    logger.info("weekly_engine start day=%s keyword=%s location=%s", d, keyword, location)
    if d in ("mon", "tue", "wed", "thu", "fri"):
        out = _run_mon_to_fri(
            db,
            keyword=keyword,
            location=location,
            batch_size=batch_size,
            delay_seconds=delay_seconds,
            max_companies_per_source=max_companies_per_source,
            enrich_limit=enrich_limit,
            enrich_timeout_seconds=enrich_timeout_seconds,
        )
    elif d == "sat":
        out = _run_saturday(db, min_score=saturday_min_score, limit=saturday_limit)
    else:
        out = _run_sunday(db)
    return {"day": d, "result": out}
