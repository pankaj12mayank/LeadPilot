"""Weekly automation engine for company growth + manual LinkedIn expansion prep."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

import config
from backend.leadpilot.linkedin_session_cache import session_info_dict
from backend.services import (
    company_enrichment_service,
    company_ingestion_service,
    company_service,
    lead_orm_service,
    runtime_settings,
    task_queue_service,
)
from backend.utils.logger import get_logger
from database.orm.models import Company, CompanyEnrichment, Lead

logger = get_logger(__name__)

WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# STEP W2: task type classification (global login requirement map)
TASK_CLASSIFICATION: dict[str, dict[str, Any]] = {
    "public_ingestion": {"requires_login": False},
    "company_db_update": {"requires_login": False},
    "enrichment": {"requires_login": False},
    "ai_enrichment": {"requires_login": False},
    "scoring": {"requires_login": False},
    "dedupe": {"requires_login": False},
    "db_normalization": {"requires_login": False},
    "linkedin_expansion": {"requires_login": True},
    "cleanup_reporting": {"requires_login": False},
}


TASK_META: dict[str, dict[str, str]] = {
    "public_ingestion": {"task_type": "ingestion"},
    "company_db_update": {"task_type": "ingestion"},
    "enrichment": {"task_type": "enrichment"},
    "ai_enrichment": {"task_type": "ai"},
    "scoring": {"task_type": "scoring"},
    "dedupe": {"task_type": "ingestion"},
    "db_normalization": {"task_type": "ingestion"},
    "linkedin_expansion": {"task_type": "linkedin"},
    "cleanup_reporting": {"task_type": "enrichment"},
}


def classify_task(task_name: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    key = str(task_name or "").strip().lower()
    row = TASK_CLASSIFICATION.get(key, {"requires_login": False})
    meta = TASK_META.get(key, {"task_type": "ingestion"})
    task_type = str(meta.get("task_type") or "ingestion")
    cfg = runtime_settings.get_admin_config()
    pri_map = cfg.get("task_priority") or {}
    priority = str(pri_map.get(task_type) or "medium").strip().lower()
    if priority not in {"high", "medium", "low"}:
        priority = "medium"
    pl = payload if isinstance(payload, dict) else {"batch": "default"}
    return {
        "task_name": key,  # backward compatibility
        "task_type": task_type,
        "priority": priority,
        "requires_login": bool(row.get("requires_login")),
        "payload": pl,
    }


SCHEDULED_JOB_TYPES = frozenset(
    {
        "daily_auto",
        "friday_heavy",
        "saturday_linkedin",
        "sunday_report",
    }
)


SCHEDULED_JOB_TASK = {
    "daily_auto": "public_ingestion",
    "friday_heavy": "enrichment",
    "saturday_linkedin": "linkedin_expansion",
    "sunday_report": "cleanup_reporting",
}


def _precheck_session_for_task(task_name: str) -> dict[str, Any]:
    task = classify_task(task_name)
    if not bool(task.get("requires_login")):
        return {
            "checked": False,
            "paused": False,
            "requires_login": False,
            "task": task,
        }
    sess = session_info_dict()
    within = bool(sess.get("within_policy"))
    return {
        "checked": True,
        "paused": not within,
        "requires_login": True,
        "task": task,
        "session": sess,
        "instructions": (
            "Session expired. Complete manual LinkedIn login, refresh session, then re-run scheduled job."
            if not within
            else "Session valid. Proceeding with login-required task."
        ),
    }


def _job_logs_path() -> Path:
    config.ensure_data_dirs()
    root = Path(config.SESSIONS_DIR) / "job_logs"
    root.mkdir(parents=True, exist_ok=True)
    return root / "job_runs.jsonl"


def _retry_queue_path() -> Path:
    config.ensure_data_dirs()
    root = Path(config.SESSIONS_DIR) / "retry_queues"
    root.mkdir(parents=True, exist_ok=True)
    return root / "company_refresh_retry.json"


def _compute_records_processed(payload: dict[str, Any]) -> int:
    n = 0
    st = payload.get("saved_total") or {}
    n += int(st.get("created") or 0) + int(st.get("updated") or 0)
    en = payload.get("enrichment") or payload.get("refresh") or {}
    n += int(en.get("selected") or 0)
    conv = payload.get("conversion") or {}
    n += int(conv.get("created") or 0)
    return n


def _collect_errors(payload: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if payload.get("error"):
        errs.append(str(payload.get("error")))
    for r in payload.get("runs") or []:
        e = r.get("error")
        if e:
            errs.append(str(e))
    enr = payload.get("enrichment") or {}
    if enr.get("error"):
        errs.append(str(enr.get("error")))
    conv = payload.get("conversion") or {}
    for e in conv.get("errors") or []:
        errs.append(str(e))
    if payload.get("paused"):
        errs.append("paused_for_manual_login")
    return errs


def _derive_status(payload: dict[str, Any], errors: list[str]) -> str:
    if payload.get("paused"):
        return "failure"
    if not errors:
        return "success"
    rp = _compute_records_processed(payload)
    return "partial_success" if rp > 0 else "failure"


def _append_job_log(*, job_type: str, result_payload: dict[str, Any]) -> dict[str, Any]:
    errors = _collect_errors(result_payload)
    status = _derive_status(result_payload, errors)
    entry = {
        "job_type": str(job_type),
        "run_date": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "records_processed": _compute_records_processed(result_payload),
        "errors": errors,
        "retry_next_scheduled_run": status == "failure",
    }
    p = _job_logs_path()
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _retry_call(
    fn: Callable[[], Any],
    *,
    attempts: int = 3,
    base_delay: float = 0.8,
    label: str = "task",
) -> Any:
    if attempts == 3:
        try:
            attempts = int((runtime_settings.get_admin_config().get("retry_policy") or {}).get("retry_count") or attempts)
        except Exception:
            attempts = 3
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
    raw = (day or "").strip().lower()
    if not raw:
        # STEP W3: auto-detect current day on system run.
        raw = datetime.now().strftime("%a").lower()
    d = raw[:3]
    if d not in WEEKDAY_KEYS:
        raise ValueError(f"Invalid day {day!r}; expected one of: {', '.join(WEEKDAY_KEYS)}")
    return d


def _resolve_targeting_inputs(keyword: str, location: str) -> tuple[str, str]:
    cfg = runtime_settings.get_admin_config()
    tgt = cfg.get("targeting") or {}
    kw_in = str(keyword or "").strip()
    loc_in = str(location or "").strip()
    if not kw_in:
        kws = [str(x).strip() for x in (tgt.get("keywords") or []) if str(x).strip()]
        inds = [str(x).strip() for x in (tgt.get("industries") or []) if str(x).strip()]
        ctypes = [str(x).strip() for x in (tgt.get("company_types") or []) if str(x).strip()]
        pieces = (kws + inds + ctypes)[:3]
        kw_in = " ".join(pieces).strip()
    if not loc_in:
        locs = [str(x).strip() for x in (tgt.get("locations") or []) if str(x).strip()]
        if locs:
            loc_in = locs[0]
    return kw_in, loc_in


def _weekday_plan(day: str) -> dict[str, Any]:
    d = _normalize_day(day)
    enabled = runtime_settings.get_enabled_ingestion_sources()
    def _flt(xs: list[str]) -> list[str]:
        return [x for x in xs if x in enabled]
    plans: dict[str, dict[str, Any]] = {
        "mon": {
            "label": "Startup ingestion",
            "sources": _flt(["yc", "job_board"]),
            "keyword_hint": "startup",
        },
        "tue": {
            "label": "Hiring signals",
            "sources": _flt(["job_board"]),
            "keyword_hint": "hiring",
        },
        "wed": {
            "label": "Local businesses",
            "sources": _flt(["local"]),
            "keyword_hint": "local business",
        },
        "thu": {
            "label": "Website + tech enrichment",
            "sources": _flt(["builtwith", "crunchbase"]),
            "keyword_hint": "technology",
        },
        "fri": {
            "label": "Full enrichment + scoring",
            "sources": _flt(["yc", "job_board", "local", "crunchbase", "builtwith"]),
            "keyword_hint": "growth",
        },
    }
    return plans.get(d, {"label": "General", "sources": _flt(["yc", "job_board"]), "keyword_hint": ""})


def _run_mon_to_fri(
    db: Session,
    *,
    day: str,
    keyword: str,
    location: str,
    batch_size: int,
    delay_seconds: float,
    max_companies_per_source: int,
    enrich_limit: int,
    enrich_timeout_seconds: float,
) -> dict[str, Any]:
    keyword, location = _resolve_targeting_inputs(keyword, location)
    plan = _weekday_plan(day)
    day_label = str(plan.get("label") or "")
    sources = list(plan.get("sources") or [])
    keyword_hint = str(plan.get("keyword_hint") or "").strip()
    run_keyword = keyword if str(keyword or "").strip() else keyword_hint
    runs: list[dict[str, Any]] = []
    saved_total = {"created": 0, "updated": 0, "skipped": 0}
    failed_items = 0
    for src in sources:
        seeds = company_ingestion_service.default_seed_urls_for_source(
            source=src,
            keyword=run_keyword,
            location=location,
        )
        if not seeds:
            runs.append({"source": src, "status": "skipped", "reason": "no_seed_urls"})
            continue
        try:
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
            runs.append({"source": src, "status": "ok", "fetched": fetched, "saved": saved})
        except Exception as e:  # noqa: BLE001
            failed_items += 1
            runs.append({"source": src, "status": "failed", "error": str(e)})
            continue
    try:
        enrich_stats = _retry_call(
            lambda: company_enrichment_service.enrich_companies_batch(
                db,
                limit=enrich_limit,
                timeout_seconds=enrich_timeout_seconds,
                delay_seconds=min(2.0, delay_seconds),
            ),
            label="enrich",
        )
    except Exception as e:  # noqa: BLE001
        failed_items += 1
        enrich_stats = {"selected": 0, "ok": 0, "failed": 0, "skipped": 0, "error": str(e)}
    db.commit()
    logger.info("weekly_engine %s done: saved=%s enrich=%s", day_label or day, saved_total, enrich_stats)
    return {
        "schedule_label": day_label,
        "runs": runs,
        "saved_total": saved_total,
        "failed_items": failed_items,
        "enrichment": enrich_stats,
        "tasks": [
            classify_task("public_ingestion", payload={"batch": "sources"}),
            classify_task("enrichment", payload={"batch": "enrich_limit"}),
            classify_task("scoring", payload={"batch": "enrich_limit"}),
        ],
    }


def _run_friday_heavy(
    db: Session,
    *,
    enrich_timeout_seconds: float,
    delay_seconds: float,
) -> dict[str, Any]:
    """
    STEP W5: Weekly Heavy Job (Friday)
    - re-enrich all companies
    - recalculate all scores (through enrichment pass)
    - remove duplicates
    - normalize DB source/domain/website fields
    """
    companies = list(db.scalars(select(Company).order_by(Company.id.asc())))
    normalization_updates = 0
    domain_fixes = 0
    source_fixes = 0
    website_fixes = 0
    dedup_removed = 0

    by_domain: dict[str, Company] = {}
    dup_ids: list[int] = []
    for c in companies:
        old_domain = str(c.domain or "").strip().lower()
        norm_domain = company_service.normalize_company_domain(c.website or c.domain)
        norm_source = company_service.normalize_company_source(c.source)
        if norm_domain and norm_domain != old_domain:
            c.domain = norm_domain
            domain_fixes += 1
            normalization_updates += 1
        if norm_source != (c.source or ""):
            c.source = norm_source
            source_fixes += 1
            normalization_updates += 1
        if norm_domain and not str(c.website or "").strip():
            c.website = f"https://{norm_domain}"
            website_fixes += 1
            normalization_updates += 1

        key = str(c.domain or "").strip().lower()
        if not key:
            continue
        if key not in by_domain:
            by_domain[key] = c
        else:
            keep = by_domain[key]
            drop = c
            keep_enr = db.scalar(select(CompanyEnrichment).where(CompanyEnrichment.company_id == keep.id).limit(1))
            drop_enr = db.scalar(select(CompanyEnrichment).where(CompanyEnrichment.company_id == drop.id).limit(1))
            if keep_enr is None and drop_enr is not None:
                drop_enr.company_id = keep.id
            elif keep_enr is not None and drop_enr is not None:
                db.execute(delete(CompanyEnrichment).where(CompanyEnrichment.company_id == drop.id))
            dup_ids.append(drop.id)

    if dup_ids:
        db.execute(delete(Company).where(Company.id.in_(dup_ids)))
        dedup_removed = len(dup_ids)
    db.flush()

    all_ids = list(db.scalars(select(Company.id).order_by(Company.id.asc())))
    refreshed = {"selected": 0, "ok": 0, "failed": 0, "skipped": 0}
    chunk = 100
    failed_items = 0
    for i in range(0, len(all_ids), chunk):
        part = all_ids[i : i + chunk]
        try:
            stats = company_enrichment_service.enrich_companies_batch(
                db,
                company_ids=part,
                limit=len(part),
                timeout_seconds=enrich_timeout_seconds,
                delay_seconds=min(2.0, max(0.1, delay_seconds)),
            )
        except Exception as e:  # noqa: BLE001
            failed_items += 1
            stats = {"selected": len(part), "ok": 0, "failed": len(part), "skipped": 0, "error": str(e)}
        refreshed["selected"] += int(stats.get("selected") or 0)
        refreshed["ok"] += int(stats.get("ok") or 0)
        refreshed["failed"] += int(stats.get("failed") or 0)
        refreshed["skipped"] += int(stats.get("skipped") or 0)
    db.commit()

    return {
        "schedule_label": "Weekly Heavy Refresh",
        "tasks": [
            classify_task("enrichment", payload={"batch": "all_companies"}),
            classify_task("scoring", payload={"batch": "all_companies"}),
            classify_task("dedupe", payload={"batch": "domain"}),
            classify_task("db_normalization", payload={"batch": "all_companies"}),
        ],
        "normalization": {
            "updated_rows": normalization_updates,
            "domain_fixes": domain_fixes,
            "source_fixes": source_fixes,
            "website_fixes": website_fixes,
        },
        "dedupe": {"removed_companies": dedup_removed},
        "failed_items": failed_items,
        "refresh": refreshed,
    }


def _run_saturday(
    db: Session,
    *,
    min_score: float,
    limit: int,
    manual_profiles: list[dict[str, Any]] | None = None,
    require_fresh_session: bool = True,
) -> dict[str, Any]:
    # Manual LinkedIn day: no auto login, no auto profile extraction.
    sess = session_info_dict()
    if require_fresh_session and not bool(sess.get("within_policy")):
        return {
            "session": sess,
            "requires_manual_login": True,
            "paused": True,
            "task": classify_task("linkedin_expansion", payload={"batch": "manual_profiles"}),
            "instructions": "Session expired. Complete manual LinkedIn login, refresh session, then re-run Saturday job.",
            "candidates": [],
            "conversion": {"created": 0, "skipped": 0, "errors": []},
        }
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
    created = 0
    skipped = 0
    errors: list[str] = []
    for raw in (manual_profiles or []):
        try:
            company_id = int(raw.get("company_id") or 0)
            name = str(raw.get("name") or "").strip()
            role = str(raw.get("role") or "").strip()
            profile_link = str(raw.get("profile_link") or "").strip()
            if company_id <= 0 or not name or "linkedin.com/in/" not in profile_link.lower():
                skipped += 1
                continue
            company = db.get(Company, company_id)
            if company is None:
                skipped += 1
                continue
            dup = db.scalar(
                select(Lead.id).where(func.lower(func.trim(Lead.linkedin_url)) == profile_link.strip().lower()).limit(1)
            )
            if dup is not None:
                skipped += 1
                continue
            lead_orm_service.create_lead(
                db,
                {
                    "full_name": name,
                    "title": role,
                    "company_name": str(company.company_name or "").strip(),
                    "company_website": str(company.website or "").strip(),
                    "linkedin_url": profile_link,
                    "source_platform": "linkedin",
                    "notes": f"Created by Saturday LinkedIn expansion job (company_id={company.id}).",
                },
            )
            created += 1
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
    db.commit()
    logger.info("weekly_engine saturday prepared candidates=%s", len(candidates))
    return {
        "session": sess,
        "requires_manual_login": not bool(sess.get("within_policy")),
        "paused": False,
        "task": classify_task("linkedin_expansion", payload={"batch": "manual_profiles"}),
        "instructions": "Open LinkedIn manually, search each query, and use /companies/linkedin/create-lead.",
        "candidates": candidates,
        "conversion": {"created": created, "skipped": skipped, "errors": errors},
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
        "total_companies": int(db.scalar(select(func.count(Company.id))) or 0),
        "total_leads": int(db.scalar(select(func.count(Lead.id))) or 0),
        "hot_leads": int(db.scalar(select(func.count(Lead.id)).where(func.lower(Lead.tier) == "hot")) or 0),
        "enriched_total": int(db.scalar(select(func.count(CompanyEnrichment.id))) or 0),
        "high_priority_companies": int(
            db.scalar(select(func.count(CompanyEnrichment.id)).where(func.lower(CompanyEnrichment.priority) == "hot"))
            or 0
        ),
        "trimmed_content_rows": trimmed,
    }
    report_file = _write_weekly_report_file(report)
    report["report_file"] = report_file
    db.commit()
    logger.info("weekly_engine sunday cleanup/report: %s", report)
    return {
        "task": classify_task("cleanup_reporting", payload={"batch": "weekly"}),
        **report,
    }


def _write_weekly_report_file(report: dict[str, Any]) -> str:
    config.ensure_data_dirs()
    root = Path(config.SESSIONS_DIR) / "weekly_reports"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    path = root / f"weekly_report_{stamp}.json"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report": report,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return str(path)


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


def _continuous_refresh_companies(
    db: Session,
    *,
    stale_days: int = 7,
    timeout_seconds: float = 10.0,
    delay_seconds: float = 0.5,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=max(1, int(stale_days or 7)))
    stale_ids: list[int] = []
    retry_queue: list[dict[str, Any]] = []
    refreshed = {"selected": 0, "ok": 0, "failed": 0, "skipped": 0}

    rows = list(db.execute(select(Company, CompanyEnrichment).outerjoin(CompanyEnrichment, CompanyEnrichment.company_id == Company.id)))
    for c, e in rows:
        last_upd = _parse_iso_dt(c.last_updated)
        is_stale = (last_upd is None) or (last_upd <= stale_cutoff)
        incomplete = (
            e is None
            or not bool(getattr(e, "fetch_ok", 0))
            or not str(getattr(e, "content_text", "") or "").strip()
            or float(getattr(e, "score", 0) or 0) <= 0
        )
        if is_stale:
            stale_ids.append(int(c.id))
        if incomplete:
            retry_queue.append(
                {
                    "company_id": int(c.id),
                    "domain": str(c.domain or ""),
                    "reason": "incomplete_data",
                    "queued_at": now.isoformat(timespec="seconds"),
                }
            )

    if stale_ids:
        chunk = 100
        for i in range(0, len(stale_ids), chunk):
            part = stale_ids[i : i + chunk]
            try:
                stats = company_enrichment_service.enrich_companies_batch(
                    db,
                    company_ids=part,
                    limit=len(part),
                    timeout_seconds=timeout_seconds,
                    delay_seconds=min(2.0, max(0.1, delay_seconds)),
                )
            except Exception:
                stats = {"selected": len(part), "ok": 0, "failed": len(part), "skipped": 0}
            refreshed["selected"] += int(stats.get("selected") or 0)
            refreshed["ok"] += int(stats.get("ok") or 0)
            refreshed["failed"] += int(stats.get("failed") or 0)
            refreshed["skipped"] += int(stats.get("skipped") or 0)

    qp = _retry_queue_path()
    with open(qp, "w", encoding="utf-8") as f:
        json.dump({"generated_at": now.isoformat(timespec="seconds"), "items": retry_queue}, f, indent=2, ensure_ascii=False)
        f.write("\n")

    db.commit()
    return {
        "stale_days": stale_days,
        "stale_companies": len(stale_ids),
        "re_enrichment": refreshed,
        "retry_queue_count": len(retry_queue),
        "retry_queue_file": str(qp),
    }


def _ai_enrichment_preview(db: Session, *, limit: int = 20) -> list[dict[str, Any]]:
    """
    Lightweight AI-style enrichment preview for daily automation reporting.
    This is intentionally non-destructive (no extra credential/API requirements).
    """
    lim = max(1, min(int(limit or 20), 100))
    stmt = (
        select(Company, CompanyEnrichment)
        .join(CompanyEnrichment, CompanyEnrichment.company_id == Company.id)
        .order_by(CompanyEnrichment.last_checked.desc())
        .limit(lim)
    )
    rows: list[dict[str, Any]] = []
    for c, e in db.execute(stmt).all():
        txt = str(e.content_text or "").strip()
        summary = txt[:180] if txt else f"{c.company_name} is in active monitoring for enrichment updates."
        problems: list[str] = []
        if bool(e.signal_content_gap):
            problems.append("Limited content presence may reduce inbound trust.")
        if bool(e.signal_ads_gap):
            problems.append("No visible marketing signal detected on homepage.")
        if bool(e.signal_hiring):
            problems.append("Hiring momentum suggests growth pressure and process needs.")
        if not problems:
            problems.append("No major risk detected; monitor messaging opportunities.")
        rows.append(
            {
                "company_id": c.id,
                "company_name": c.company_name,
                "summary": summary,
                "problems": problems[:2],
            }
        )
    return rows


def run_daily_auto_job(
    db: Session,
    *,
    keyword: str = "software",
    location: str = "",
    batch_size: int = 10,
    delay_seconds: float = 1.0,
    max_companies_per_source: int = 80,
    enrich_limit: int = 20,
    enrich_timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """
    STEP W4: Daily Auto Job (no login required).
    Tasks:
    - public ingestion
    - company DB upsert/update
    - website enrichment
    - signal detection
    - AI enrichment preview
    - score refresh
    """
    bs = max(10, min(int(batch_size or 10), 20))
    dly = max(0.2, min(float(delay_seconds or 1.0), 8.0))
    max_per_source = max(1, min(int(max_companies_per_source or 80), 500))
    keyword, location = _resolve_targeting_inputs(keyword, location)
    ingest_sources = [s for s in runtime_settings.get_enabled_ingestion_sources() if s != "manual"]
    if not ingest_sources:
        ingest_sources = ["yc"]

    runs: list[dict[str, Any]] = []
    saved_total = {"created": 0, "updated": 0, "skipped": 0}
    failed_sources = 0
    failed_items = 0

    for src in ingest_sources:
        seeds = company_ingestion_service.default_seed_urls_for_source(source=src, keyword=keyword, location=location)
        if not seeds:
            runs.append({"source": src, "status": "skipped", "reason": "no_seed_urls"})
            continue
        try:
            candidates, fetched = company_ingestion_service.collect_companies_from_source_pages(
                source=src,
                seed_urls=seeds,
                batch_size=bs,
                delay_seconds=dly,
                max_companies=max_per_source,
            )
            saved = company_service.ingest_public_companies(db, candidates, default_source=src)
            saved_total["created"] += int(saved.get("created") or 0)
            saved_total["updated"] += int(saved.get("updated") or 0)
            saved_total["skipped"] += int(saved.get("skipped") or 0)
            runs.append({"source": src, "status": "ok", "fetched": fetched, "saved": saved})
        except Exception as e:  # noqa: BLE001
            failed_sources += 1
            failed_items += 1
            runs.append({"source": src, "status": "failed", "error": str(e)})
            continue

    try:
        enrich_stats = company_enrichment_service.enrich_companies_batch(
            db,
            limit=max(1, min(int(enrich_limit or 20), 100)),
            timeout_seconds=max(2.0, min(float(enrich_timeout_seconds or 10.0), 30.0)),
            delay_seconds=min(2.0, dly),
        )
    except Exception as e:  # noqa: BLE001
        failed_items += 1
        enrich_stats = {"selected": 0, "ok": 0, "failed": 0, "skipped": 0, "error": str(e)}
    try:
        ai_preview = _ai_enrichment_preview(db, limit=min(20, int(enrich_limit or 20)))
    except Exception as e:  # noqa: BLE001
        failed_items += 1
        ai_preview = [{"company_id": 0, "company_name": "", "summary": "", "problems": [str(e)]}]
    db.commit()

    refreshed_scores = int(
        db.scalar(
            select(func.count(CompanyEnrichment.id)).where(CompanyEnrichment.last_checked != "")
        )
        or 0
    )
    continuous_refresh = _continuous_refresh_companies(
        db,
        stale_days=7,
        timeout_seconds=max(2.0, min(float(enrich_timeout_seconds or 10.0), 30.0)),
        delay_seconds=min(2.0, dly),
    )
    out = {
        "tasks": [
            classify_task("public_ingestion", payload={"batch": "sources"}),
            classify_task("company_db_update", payload={"batch": "upsert"}),
            classify_task("enrichment", payload={"batch": "enrich_limit"}),
            classify_task("ai_enrichment", payload={"batch": "preview"}),
            classify_task("scoring", payload={"batch": "enrich_limit"}),
        ],
        "runs": runs,
        "saved_total": saved_total,
        "failed_items": failed_items,
        "failed_sources": failed_sources,
        "enrichment": enrich_stats,
        "ai_enrichment_preview": ai_preview,
        "score_refresh": {"refreshed_companies": refreshed_scores},
        "continuous_refresh": continuous_refresh,
        "batch_size": bs,
        "delay_seconds": dly,
    }
    out["job_log"] = _append_job_log(job_type="daily_auto_job", result_payload=out)
    return out


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
    saturday_manual_profiles: list[dict[str, Any]] | None = None,
    saturday_require_fresh_session: bool = True,
) -> dict[str, Any]:
    """
    Weekly automation orchestrator.

    Mon-Fri: ingestion -> enrichment -> scoring
    Saturday: manual LinkedIn expansion prep (session check + candidate list)
    Sunday: cleanup + reporting
    """
    d = _normalize_day(day)
    logger.info("weekly_engine start day=%s keyword=%s location=%s", d, keyword, location)
    try:
        if d in ("mon", "tue", "wed", "thu"):
            out = _run_mon_to_fri(
                db,
                day=d,
                keyword=keyword,
                location=location,
                batch_size=batch_size,
                delay_seconds=delay_seconds,
                max_companies_per_source=max_companies_per_source,
                enrich_limit=enrich_limit,
                enrich_timeout_seconds=enrich_timeout_seconds,
            )
        elif d == "fri":
            out = _run_friday_heavy(
                db,
                enrich_timeout_seconds=enrich_timeout_seconds,
                delay_seconds=delay_seconds,
            )
        elif d == "sat":
            out = _run_saturday(
                db,
                min_score=saturday_min_score,
                limit=saturday_limit,
                manual_profiles=saturday_manual_profiles,
                require_fresh_session=saturday_require_fresh_session,
            )
        else:
            out = _run_sunday(db)
    except Exception as e:  # noqa: BLE001
        out = {"schedule_label": "Weekly Run", "error": str(e), "runs": [], "saved_total": {"created": 0, "updated": 0, "skipped": 0}}
    resp = {
        "day": d,
        "result": out,
        "task_classification": TASK_CLASSIFICATION,
    }
    resp["job_log"] = _append_job_log(job_type=f"weekly_{d}", result_payload=out if isinstance(out, dict) else {})
    return resp


def run_scheduled_job(
    db: Session,
    *,
    job_type: str,
    keyword: str = "software",
    location: str = "",
    batch_size: int = 10,
    delay_seconds: float = 1.0,
    enqueue_only: bool = True,
) -> dict[str, Any]:
    """
    STEP W11 system entry point for cron-based scheduler.
    Accepts job_type and dispatches to the correct engine branch.
    """
    jt = str(job_type or "").strip().lower()
    if jt not in SCHEDULED_JOB_TYPES:
        raise ValueError(f"Unsupported job_type {job_type!r}; expected one of: {', '.join(sorted(SCHEDULED_JOB_TYPES))}")
    if enqueue_only:
        queued: list[dict[str, Any]] = []
        if jt == "daily_auto":
            queued.append(
                task_queue_service.enqueue(
                    {
                        "task_type": "ingestion",
                        "priority": _priority_for_task_type("ingestion"),
                        "requires_login": False,
                        "payload": {
                            "batch": "daily_auto",
                            "keyword": keyword,
                            "location": location,
                            "batch_size": batch_size,
                            "delay_seconds": delay_seconds,
                        },
                    },
                    db=db,
                )
            )
        elif jt == "friday_heavy":
            queued.append(
                task_queue_service.enqueue(
                    {
                        "task_type": "enrichment",
                        "priority": _priority_for_task_type("enrichment"),
                        "requires_login": False,
                        "payload": {"batch": "friday_heavy"},
                    },
                    db=db,
                )
            )
            queued.append(
                task_queue_service.enqueue(
                    {
                        "task_type": "ai",
                        "priority": _priority_for_task_type("scoring"),
                        "requires_login": False,
                        "payload": {"batch": "friday_heavy"},
                    },
                    db=db,
                )
            )
            queued.append(
                task_queue_service.enqueue(
                    {
                        "task_type": "scoring",
                        "priority": _priority_for_task_type("scoring"),
                        "requires_login": False,
                        "payload": {"batch": "friday_heavy"},
                    },
                    db=db,
                )
            )
        elif jt == "saturday_linkedin":
            cfg = runtime_settings.get_admin_config()
            day_for_linkedin = str((cfg.get("scheduler_config") or {}).get("linkedin_day") or "sat").strip().lower()[:3] or "sat"
            queued.append(
                task_queue_service.enqueue(
                    {
                        "task_type": "linkedin",
                        "priority": _priority_for_task_type("linkedin"),
                        "requires_login": True,
                        "payload": {"batch": "saturday_linkedin", "day": day_for_linkedin},
                    },
                    db=db,
                )
            )
        else:
            queued.append(
                task_queue_service.enqueue(
                    {
                        "task_type": "enrichment",
                        "priority": _priority_for_task_type("enrichment"),
                        "requires_login": False,
                        "payload": {"batch": "sunday_report", "mode": "weekly_cleanup"},
                    },
                    db=db,
                )
            )
            queued.append(
                task_queue_service.enqueue(
                    {
                        "task_type": "scoring",
                        "priority": _priority_for_task_type("scoring"),
                        "requires_login": False,
                        "payload": {"batch": "sunday_report"},
                    },
                    db=db,
                )
            )
        return {
            "job_type": jt,
            "mode": "queue_only",
            "enqueued_count": len(queued),
            "tasks": queued,
            "queue_size": task_queue_service.size(db=db),
            "waiting_queue_size": task_queue_service.waiting_size(db=db),
            "scheduler_config": runtime_settings.get_admin_config().get("scheduler_config"),
        }

    gate = _precheck_session_for_task(SCHEDULED_JOB_TASK.get(jt, ""))
    if gate.get("paused"):
        paused_result = {
            "paused": True,
            "requires_manual_login": True,
            "task": gate.get("task"),
            "session": gate.get("session") or {},
            "instructions": gate.get("instructions") or "Session expired. Re-login and retry.",
            "conversion": {"created": 0, "skipped": 0, "errors": []},
        }
        return {"job_type": jt, "session_gate": gate, "result": paused_result}
    if jt == "daily_auto":
        out = run_daily_auto_job(
            db,
            keyword=keyword,
            location=location,
            batch_size=batch_size,
            delay_seconds=delay_seconds,
        )
    elif jt == "friday_heavy":
        out = run_weekly_engine(
            db,
            day="fri",
            keyword=keyword,
            location=location,
            batch_size=batch_size,
            delay_seconds=delay_seconds,
        )
    elif jt == "saturday_linkedin":
        cfg = runtime_settings.get_admin_config()
        day_for_linkedin = str((cfg.get("scheduler_config") or {}).get("linkedin_day") or "sat").strip().lower()[:3] or "sat"
        out = run_weekly_engine(
            db,
            day=day_for_linkedin,
            keyword=keyword,
            location=location,
            batch_size=batch_size,
            delay_seconds=delay_seconds,
            saturday_require_fresh_session=False,
        )
    else:
        out = run_weekly_engine(
            db,
            day="sun",
            keyword=keyword,
            location=location,
            batch_size=batch_size,
            delay_seconds=delay_seconds,
        )
    return {
        "job_type": jt,
        "session_gate": gate,
        "scheduler_config": runtime_settings.get_admin_config().get("scheduler_config"),
        "result": out,
    }


def _priority_for_task_type(task_type: str) -> str:
    cfg = runtime_settings.get_admin_config()
    p = str((cfg.get("task_priority") or {}).get(task_type) or "").strip().lower()
    if not p and str(task_type or "").strip().lower() == "ai":
        p = str((cfg.get("queue_priority") or {}).get("ai") or "medium").strip().lower()
    if not p:
        p = "medium"
    return p if p in {"high", "medium", "low"} else "medium"
