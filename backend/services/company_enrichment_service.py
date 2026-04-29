"""Website enrichment for companies (safe, timeout-limited, no heavy crawling)."""

from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.enrichment.signals import build_signals
from backend.enrichment.website import fetch_website_enrichment
from backend.lead_scoring.tiers import assign_tier, tier_label
from backend.ollama_messaging.ollama_service import OllamaGenerateService
from backend.services import external_llm_service
from backend.services import runtime_settings
from backend.services.scoring_engine_service import composite_score
from backend.settings.lead_schema import utc_now_iso
from backend.utils.logger import get_logger
from database.orm.models import Company, CompanyEnrichment

logger = get_logger(__name__)

def enrichment_to_dict(row: CompanyEnrichment | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "company_id": row.company_id,
        "source_url": row.source_url,
        "has_blog": bool(row.has_blog),
        "has_careers": bool(row.has_careers),
        "content_text": row.content_text or "",
        "signal_hiring": bool(row.signal_hiring),
        "signal_scaling": bool(row.signal_scaling),
        "signal_content_gap": bool(row.signal_content_gap),
        "signal_ads_gap": bool(row.signal_ads_gap),
        "score": float(row.score or 0),
        "priority": row.priority or "",
        "fetch_ok": bool(row.fetch_ok),
        "fetch_error": row.fetch_error or "",
        "company_summary": row.ai_summary or "",
        "problems": [x for x in str(row.ai_problems or "").split("\n") if x.strip()],
        "opportunity_insight": row.ai_opportunity or "",
        "ai_score": float(row.ai_score or 0),
        "ai_provider": row.ai_provider or "",
        "last_checked": row.last_checked,
    }


def get_company_enrichment(db: Session, company_id: int) -> CompanyEnrichment | None:
    return db.scalar(select(CompanyEnrichment).where(CompanyEnrichment.company_id == int(company_id)).limit(1))


def _company_signal_score(*, signals: dict[str, bool], has_content: bool, website_present: bool, fetch_ok: bool, ai_score: float) -> tuple[float, str]:
    signal_score = 0.0
    if signals.get("hiring"):
        signal_score += 40.0
    if signals.get("scaling"):
        signal_score += 35.0
    if signals.get("content_gap"):
        signal_score += 12.5
    if signals.get("ads_gap"):
        signal_score += 12.5
    data_completeness = 0.0
    if website_present:
        data_completeness += 40.0
    if fetch_ok:
        data_completeness += 35.0
    if has_content:
        data_completeness += 25.0
    role_relevance = 70.0 if signals.get("hiring") else 55.0 if signals.get("scaling") else 45.0
    out = composite_score(
        role_relevance=role_relevance,
        signals=min(100.0, signal_score),
        data_completeness=min(100.0, data_completeness),
        ai_score=float(ai_score or 0.0),
    )
    return float(out["score"]), tier_label(str(out["tier"]))


def _parse_json_obj(raw: str | None) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _fallback_qualification(*, company: Company, signals: dict[str, bool]) -> dict[str, Any]:
    name = str(company.company_name or company.domain or "This company").strip()
    active = [k for k, v in signals.items() if bool(v)]
    summary = f"{name} shows active digital intent signals and can be prioritized for targeted outreach."
    if active:
        summary = f"{name} signals {', '.join(active[:3])}, indicating near-term buying or growth activity."
    problems = [
        "Lead qualification context is fragmented across public data points.",
        "Signal-to-action mapping is not consistently prioritized for outreach.",
        "Growth indicators are present but not converted into a focused campaign plan.",
    ]
    opportunity = "Prioritize this account with a signal-led outreach sequence and a concise value proposition test."
    ai_score = 55 + min(40, 10 * len(active))
    return {
        "company_summary": summary,
        "problems": problems,
        "opportunity_insight": opportunity,
        "ai_score": max(1, min(100, int(ai_score))),
        "ai_provider": "fallback",
    }


def _qualification_cache_key(*, company: Company, enrichment: CompanyEnrichment, signals: dict[str, bool]) -> str:
    payload = {
        "company_name": str(company.company_name or ""),
        "domain": str(company.domain or ""),
        "website": str(company.website or ""),
        "content": str(enrichment.content_text or "")[:2000],
        "signals": {k: bool(v) for k, v in sorted((signals or {}).items())},
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _generate_ai_qualification(*, company: Company, enrichment: CompanyEnrichment, signals: dict[str, bool]) -> dict[str, Any]:
    provider = runtime_settings.get_ai_provider()
    retry_cfg = runtime_settings.get_admin_config().get("retry_policy") or {}
    attempts = max(1, min(5, int(retry_cfg.get("retry_count") or 2)))
    prompt = (
        "Return JSON only with keys: company_summary, problems, opportunity_insight, ai_score.\n"
        "Rules: problems must be exactly 3 concise strings. ai_score must be integer 1-100.\n"
        f"company_name={company.company_name}\n"
        f"website={company.website}\n"
        f"domain={company.domain}\n"
        f"signals={json.dumps(signals, ensure_ascii=True)}\n"
        f"content_sample={str(enrichment.content_text or '')[:1600]}"
    )
    system = "You are a B2B qualification engine."

    def _try_external() -> dict[str, Any] | None:
        if not runtime_settings.get_external_api_key():
            return None
        for _ in range(attempts):
            try:
                raw = external_llm_service.chat_completion_json(system=system, user=prompt)
            except Exception:
                continue
            obj = _parse_json_obj(raw)
            if obj:
                return obj
        return None

    def _try_ollama() -> dict[str, Any] | None:
        if not runtime_settings.get_use_ollama():
            return None
        client = OllamaGenerateService(timeout_seconds=8.0, max_retries=1)
        model = runtime_settings.get_model_name()
        for _ in range(attempts):
            try:
                raw = client.generate_text(model, prompt, system=system)
            except Exception:
                continue
            obj = _parse_json_obj(raw)
            if obj:
                return obj
        return None

    obj: dict[str, Any] | None = None
    used_provider = "fallback"
    if provider == "ollama":
        primary = _try_ollama()
        if primary:
            obj = primary
            used_provider = "ollama"
        else:
            secondary = _try_external()
            if secondary:
                obj = secondary
                used_provider = "external_api"
    elif provider == "external_api":
        primary = _try_external()
        if primary:
            obj = primary
            used_provider = "external_api"
        else:
            secondary = _try_ollama()
            if secondary:
                obj = secondary
                used_provider = "ollama"
    elif provider == "none":
        obj = None
    if not obj:
        fb = _fallback_qualification(company=company, signals=signals)
        return fb
    problems = obj.get("problems")
    if isinstance(problems, str):
        problems = [x.strip(" -") for x in re.split(r"[\n;]+", problems) if x.strip()]
    if not isinstance(problems, list):
        problems = []
    clean_problems = [str(x).strip() for x in problems if str(x).strip()][:3]
    while len(clean_problems) < 3:
        clean_problems.append(f"Qualification gap {len(clean_problems) + 1} needs review.")
    try:
        ai_score = int(float(obj.get("ai_score") or 0))
    except Exception:
        ai_score = 0
    if ai_score < 1 or ai_score > 100:
        ai_score = _fallback_qualification(company=company, signals=signals)["ai_score"]
    return {
        "company_summary": str(obj.get("company_summary") or "").strip() or _fallback_qualification(company=company, signals=signals)["company_summary"],
        "problems": clean_problems,
        "opportunity_insight": str(obj.get("opportunity_insight") or "").strip()
        or _fallback_qualification(company=company, signals=signals)["opportunity_insight"],
        "ai_score": ai_score,
        "ai_provider": used_provider,
    }


def upsert_company_ai_qualification(
    db: Session,
    *,
    company: Company,
    enrichment: CompanyEnrichment,
    signals: dict[str, bool],
) -> dict[str, Any]:
    now = utc_now_iso()
    key = _qualification_cache_key(company=company, enrichment=enrichment, signals=signals)
    if str(enrichment.ai_cache_key or "") == key and str(enrichment.ai_summary or "").strip():
        logger.info("ai.qualification.cache_hit company_id=%s", int(company.id))
        return {
            "company_summary": enrichment.ai_summary,
            "problems": [x for x in str(enrichment.ai_problems or "").split("\n") if x.strip()][:3],
            "opportunity_insight": enrichment.ai_opportunity or "",
            "ai_score": int(float(enrichment.ai_score or 0)),
            "ai_provider": enrichment.ai_provider or "cache",
            "cached": True,
        }
    qual = _generate_ai_qualification(company=company, enrichment=enrichment, signals=signals)
    logger.info(
        "ai.qualification.generated company_id=%s provider=%s score=%s",
        int(company.id),
        str(qual.get("ai_provider") or "fallback"),
        int(qual.get("ai_score") or 0),
    )
    enrichment.ai_summary = str(qual.get("company_summary") or "")[:3000]
    enrichment.ai_problems = "\n".join([str(x).strip() for x in (qual.get("problems") or []) if str(x).strip()][:3])
    enrichment.ai_opportunity = str(qual.get("opportunity_insight") or "")[:3000]
    enrichment.ai_score = float(max(1, min(100, int(qual.get("ai_score") or 1))))
    enrichment.ai_provider = str(qual.get("ai_provider") or "fallback")
    enrichment.ai_cache_key = key
    enrichment.ai_updated_at = now
    company.ai_score = float(enrichment.ai_score or 0.0)
    db.flush()
    return {**qual, "cached": False}


def upsert_company_enrichment(
    db: Session,
    *,
    company: Company,
    timeout_seconds: float = 10.0,
    max_text_chars: int = 4000,
) -> CompanyEnrichment:
    """
    Enrich one company from homepage URL.

    Rules:
    - broken website -> keep enrichment row with ``fetch_ok=0`` and error text
    - timeout enforced via website fetch call
    - no deep scraping; homepage-only heuristics + short text sample
    """
    now = utc_now_iso()
    url = str(company.website or "").strip()
    logger.info("enrichment.start company_id=%s domain=%s", int(company.id), str(company.domain or ""))
    existing = get_company_enrichment(db, company.id)
    if not url:
        if existing is None:
            existing = CompanyEnrichment(
                company_id=company.id,
                source_url="",
                has_blog=0,
                has_careers=0,
                content_text="",
                fetch_ok=0,
                fetch_error="missing_website",
                signal_hiring=0,
                signal_scaling=0,
                signal_content_gap=0,
                signal_ads_gap=0,
                score=0.0,
                priority="Cold",
                last_checked=now,
            )
            db.add(existing)
        else:
            existing.fetch_ok = 0
            existing.fetch_error = "missing_website"
            existing.signal_hiring = 0
            existing.signal_scaling = 0
            existing.signal_content_gap = 0
            existing.signal_ads_gap = 0
            existing.score = 0.0
            existing.priority = "Cold"
            existing.last_checked = now
        db.flush()
        db.refresh(existing)
        logger.info("enrichment.skip company_id=%s reason=missing_website", int(company.id))
        return existing

    ws = fetch_website_enrichment(url, timeout=float(timeout_seconds))
    if existing is None:
        existing = CompanyEnrichment(company_id=company.id)
        db.add(existing)
    existing.source_url = str(ws.final_url or ws.url or url)[:2000]
    existing.has_blog = 1 if ws.has_blog else 0
    existing.has_careers = 1 if ws.is_hiring else 0
    existing.content_text = str(ws.text_sample or "")[: max(200, int(max_text_chars))]
    sig = build_signals(
        ws,
        {
            "company_name": company.company_name,
            "website": company.website,
            "notes": ws.text_sample,
        },
    )
    existing.signal_hiring = 1 if sig.get("hiring") else 0
    existing.signal_scaling = 1 if sig.get("scaling") else 0
    existing.signal_content_gap = 1 if sig.get("content_gap") else 0
    existing.signal_ads_gap = 1 if sig.get("ads_gap") else 0
    sc, pri = _company_signal_score(
        signals=sig,
        has_content=bool(existing.content_text),
        website_present=bool(url),
        fetch_ok=bool(ws.ok),
        ai_score=float(existing.ai_score or 0.0),
    )
    existing.last_checked = now
    ai_pack = upsert_company_ai_qualification(db, company=company, enrichment=existing, signals=sig)
    final_score, final_priority = _company_signal_score(
        signals=sig,
        has_content=bool(existing.content_text),
        website_present=bool(url),
        fetch_ok=bool(ws.ok),
        ai_score=float(ai_pack.get("ai_score") or 0.0),
    )
    existing.score = float(max(1.0, min(100.0, final_score)))
    existing.priority = str(final_priority or pri)
    existing.fetch_ok = 1 if ws.ok else 0
    existing.fetch_error = str(ws.error or "")[:1500]
    existing.last_checked = now
    company.signals = ",".join([k for k, v in sig.items() if bool(v)])
    company.last_updated = now
    db.flush()
    db.refresh(existing)
    logger.info(
        "scoring.done company_id=%s score=%s priority=%s fetch_ok=%s",
        int(company.id),
        float(existing.score or 0.0),
        str(existing.priority or ""),
        int(existing.fetch_ok or 0),
    )
    return existing


def rescore_all_companies(db: Session, *, limit: int = 1000) -> dict[str, int]:
    rows = list(
        db.execute(
            select(Company, CompanyEnrichment)
            .join(CompanyEnrichment, CompanyEnrichment.company_id == Company.id)
            .limit(max(1, min(int(limit or 1000), 5000)))
        )
    )
    processed = 0
    for company, enr in rows:
        signals = {
            "hiring": bool(getattr(enr, "signal_hiring", 0)),
            "scaling": bool(getattr(enr, "signal_scaling", 0)),
            "content_gap": bool(getattr(enr, "signal_content_gap", 0)),
            "ads_gap": bool(getattr(enr, "signal_ads_gap", 0)),
        }
        sc, pri = _company_signal_score(
            signals=signals,
            has_content=bool(getattr(enr, "content_text", "")),
            website_present=bool(getattr(company, "website", "")),
            fetch_ok=bool(getattr(enr, "fetch_ok", 0)),
            ai_score=float(getattr(enr, "ai_score", 0.0) or 0.0),
        )
        enr.score = float(sc)
        enr.priority = str(pri)
        company.ai_score = float(getattr(enr, "ai_score", 0.0) or 0.0)
        processed += 1
    db.flush()
    return {"processed": processed}


def run_ai_qualification_batch(
    db: Session,
    *,
    company_ids: list[int] | None = None,
    limit: int = 50,
    live_ai: bool = False,
) -> dict[str, int]:
    lim = max(1, min(int(limit or 50), 500))
    stmt = select(Company, CompanyEnrichment).join(CompanyEnrichment, CompanyEnrichment.company_id == Company.id)
    if company_ids:
        clean = [int(x) for x in company_ids if int(x) > 0][:lim]
        stmt = stmt.where(Company.id.in_(clean))
    rows = list(db.execute(stmt.limit(lim)))
    processed = 0
    cached = 0
    for company, enr in rows:
        signals = {
            "hiring": bool(getattr(enr, "signal_hiring", 0)),
            "scaling": bool(getattr(enr, "signal_scaling", 0)),
            "content_gap": bool(getattr(enr, "signal_content_gap", 0)),
            "ads_gap": bool(getattr(enr, "signal_ads_gap", 0)),
        }
        if live_ai:
            out = upsert_company_ai_qualification(db, company=company, enrichment=enr, signals=signals)
        else:
            now = utc_now_iso()
            key = _qualification_cache_key(company=company, enrichment=enr, signals=signals)
            if str(enr.ai_cache_key or "") == key and str(enr.ai_summary or "").strip():
                out = {"cached": True}
            else:
                fb = _fallback_qualification(company=company, signals=signals)
                enr.ai_summary = str(fb.get("company_summary") or "")[:3000]
                enr.ai_problems = "\n".join([str(x).strip() for x in (fb.get("problems") or []) if str(x).strip()][:3])
                enr.ai_opportunity = str(fb.get("opportunity_insight") or "")[:3000]
                enr.ai_score = float(max(1, min(100, int(fb.get("ai_score") or 1))))
                enr.ai_provider = "fallback"
                enr.ai_cache_key = key
                enr.ai_updated_at = now
                company.ai_score = float(enr.ai_score or 0.0)
                out = {"cached": False}
        if bool(out.get("cached")):
            cached += 1
        processed += 1
    db.flush()
    return {"processed": processed, "cached": cached}


def enrich_companies_batch(
    db: Session,
    *,
    company_ids: list[int] | None = None,
    limit: int = 20,
    timeout_seconds: float = 10.0,
    delay_seconds: float = 0.4,
) -> dict[str, Any]:
    """
    Enrich up to ``limit`` companies (default 20) to keep requests light.
    """
    lim = max(1, min(int(limit or 20), 100))
    dly = max(0.1, min(float(delay_seconds or 0.4), 5.0))

    if company_ids:
        clean = [int(x) for x in company_ids if int(x) > 0][:lim]
        rows = list(db.scalars(select(Company).where(Company.id.in_(clean)).limit(lim)))
    else:
        rows = list(db.scalars(select(Company).order_by(Company.last_updated.desc(), Company.id.desc()).limit(lim)))
    ok = 0
    failed = 0
    skipped = 0
    for idx, c in enumerate(rows):
        if not str(c.website or "").strip():
            upsert_company_enrichment(db, company=c, timeout_seconds=timeout_seconds)
            skipped += 1
        else:
            enr = upsert_company_enrichment(db, company=c, timeout_seconds=timeout_seconds)
            if enr.fetch_ok:
                ok += 1
            else:
                failed += 1
        if idx < len(rows) - 1:
            time.sleep(dly)
    return {"selected": len(rows), "ok": ok, "failed": failed, "skipped": skipped}
