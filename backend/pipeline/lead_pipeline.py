"""
Single end-to-end run: LinkedIn (Playwright) -> clean -> score -> Ollama -> CSV + SQLite.
Does not use ``run_scrape_sync`` / platform registry; calls ``LinkedInScraper`` directly.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

import config as app_config
from backend.lead_cleaning.engine import run_cleaning_pipeline, STANDARD_COLUMNS
from backend.lead_scoring.engine import score_lead
from backend.lead_scoring.tiers import tier_label
from backend.modules.ai_generator.service import lead_dict_to_message_input
from backend.ollama_messaging.generator import generate_lead_messages
from backend.ollama_messaging.types import LeadMessageInput, LeadMessageOutput
from backend.scraper.config import ScraperRunConfig, ScraperRunResult
from backend.scraper.exceptions import SessionMissingError
from backend.scraper.platforms.linkedin import LinkedInScraper
from backend.scraper.progress import NullProgressSink
from backend.scraper.session_manager import SessionManager
from backend.pipeline.pipeline_sqlite import save_pipeline_run
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Manual outreach: store ``status`` in ``outreach_queue`` (e.g. New, Contacted, Replied,
# Follow-up Sent, Meeting Scheduled, Closed, Rejected).

_ENRICHED_CSV_COLS: List[str] = [
    "name",
    "title",
    "company",
    "location",
    "linkedin_url",
    "website",
    "score",
    "category",
    "company_summary",
    "pain_points",
    "opportunity_insight",
    "linkedin_message",
    "email_message",
    "followup_message",
    "message",
]

_QUEUE_CSV_COLS: List[str] = [
    "name",
    "title",
    "company",
    "location",
    "linkedin_url",
    "message",
    "email_message",
    "followup_message",
    "status",
    "score",
    "category",
]


@dataclass
class PipelineResult:
    run_id: str
    exports_dir: str
    scrape: ScraperRunResult
    raw_leads_path: str
    enriched_leads_path: str
    outreach_queue_path: str
    sqlite_path: str
    lead_count: int
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.errors and self.scrape.success


def _ensure_scrape_input_csv(
    result: ScraperRunResult, *, min_cols: List[str]
) -> str:
    p = result.csv_path or ""
    if p and os.path.isfile(p):
        return os.path.abspath(p)
    out = os.path.join(app_config.EXPORTS_DIR, f"_pipeline_empty_scrape_{result.run_id}.csv")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    pd.DataFrame([], columns=min_cols).to_csv(out, index=False)
    return out


def ensure_linkedin_browser_session(
    *,
    wait_seconds: Optional[int] = None,
) -> None:
    """
    Reuse a verified LinkedIn session if present; otherwise open a headed window for
    manual login (Playwright persistent profile under ``SESSIONS_DIR``).
    """
    w = int(wait_seconds or getattr(app_config, "SCRAPER_MANUAL_LOGIN_DEFAULT_SECONDS", 180) or 180)
    wait_ms = min(max(w, 30), 600) * 1000
    sm = SessionManager()
    if sm.session_connected("linkedin"):
        logger.info("LinkedIn session already connected (playwright_user_data/linkedin).")
        return
    logger.info("Opening browser for manual LinkedIn login (wait up to %s s).", w)
    sm.open_login_window("linkedin", wait_ms=wait_ms, start_url=None)


def run_linkedin_scrape_direct(
    cfg: ScraperRunConfig,
) -> ScraperRunResult:
    """Call ``LinkedInScraper`` directly (no ``get_scraper_class`` / registry)."""
    scraper = LinkedInScraper(cfg, progress=NullProgressSink())
    return scraper.run()


def _cell(x: Any) -> str:
    s = str(x or "").strip()
    if s.lower() in ("", "none", "nan", "null"):
        return ""
    return s


def _enrich_lead_ollama_pack(lead: Dict[str, Any], model_family: str) -> LeadMessageOutput:
    inp: LeadMessageInput = lead_dict_to_message_input(lead)
    if not str(inp.get("opportunity_summary") or "").strip():
        inp = dict(inp)
        inp["opportunity_summary"] = str(lead.get("opportunity_insight") or lead.get("notes") or "")[:2000]
    return generate_lead_messages(inp, model_family=model_family)


def run_linkedin_lead_pipeline(
    *,
    keyword: str,
    country: str = "",
    industry: str = "",
    company_size: str = "",
    max_leads: Optional[int] = None,
    exports_dir: Optional[str] = None,
    model_family: str = "llama3",
    headless: bool = False,
    profile_contact_enrich: bool = False,
    require_manual_login: bool = True,
    manual_login_wait_seconds: Optional[int] = None,
) -> PipelineResult:
    err: List[str] = []
    app_config.ensure_data_dirs()
    out_dir = os.path.abspath(exports_dir or app_config.EXPORTS_DIR)
    os.makedirs(out_dir, exist_ok=True)
    run_id = str(uuid.uuid4())
    if require_manual_login:
        ensure_linkedin_browser_session(wait_seconds=manual_login_wait_seconds)

    max_n = int(max_leads or app_config.SCRAPER_MAX_LEADS_DEFAULT)
    max_n = max(1, min(max_n, int(getattr(app_config, "SCRAPER_MAX_LEADS_HARD_CAP", 50) or 50)))

    lo, hi = 3.0, 5.0
    cfg = ScraperRunConfig(
        platform="linkedin",
        keyword=keyword or "",
        country=country or "",
        industry=industry or "",
        company_size=company_size or "",
        max_leads=max_n,
        delay_min_seconds=lo,
        delay_max_seconds=hi,
        headless=headless,
        max_scroll_rounds=12,
        profile_contact_enrich=bool(profile_contact_enrich),
    )

    try:
        scrape = run_linkedin_scrape_direct(cfg)
    except SessionMissingError as e:
        err.append(str(e))
        scrape = ScraperRunResult(
            run_id=str(uuid.uuid4()),
            platform="linkedin",
            collected=0,
            csv_path=None,
            errors=[str(e)],
        )
    if scrape.errors:
        for x in scrape.errors:
            sx = str(x)
            if sx not in err:
                err.append(sx)

    min_scrape_cols = [
        "full_name",
        "title",
        "company_name",
        "location",
        "linkedin_url",
        "url",
        "source_platform",
    ]
    input_csv = _ensure_scrape_input_csv(scrape, min_cols=min_scrape_cols)
    # Cleaning writes ``raw_leads.csv``, ``cleaned_leads.csv``, and cleaning-stage ``enriched_leads.csv``
    # to ``out_dir``; the step below overwrites ``enriched_leads.csv`` with the final Ollama pack.
    run_cleaning_pipeline(input_csv, exports_dir=out_dir)

    raw_p = os.path.join(out_dir, "raw_leads.csv")
    cleaning_enriched_p = os.path.join(out_dir, "enriched_leads.csv")
    if not os.path.isfile(raw_p):
        pd.DataFrame(columns=STANDARD_COLUMNS).to_csv(raw_p, index=False)
    if not os.path.isfile(cleaning_enriched_p):
        pd.DataFrame(
            columns=STANDARD_COLUMNS
            + ["email_domain", "linkedin_username", "data_quality_score"]
        ).to_csv(cleaning_enriched_p, index=False)

    try:
        if os.path.isfile(cleaning_enriched_p) and os.path.getsize(cleaning_enriched_p) > 0:
            df = pd.read_csv(cleaning_enriched_p, dtype=str, keep_default_na=False)
        else:
            df = pd.DataFrame()
    except Exception as e:  # noqa: BLE001
        logger.exception("Read enriched: %s", e)
        df = pd.DataFrame()
    rows: List[Dict[str, Any]] = df.to_dict(orient="records")
    if not rows:
        rows = []

    final_enriched: List[Dict[str, Any]] = []
    queue: List[Dict[str, Any]] = []

    for r in rows:
        lead = dict(r)
        lead["full_name"] = _cell(lead.get("full_name") or lead.get("name"))
        if not _cell(lead.get("linkedin_url")):
            continue
        if not _cell(lead.get("location")):
            lead["location"] = _cell(lead.get("filter_country") or lead.get("country"))

        sig = score_lead(lead, benchmark_industry=industry or app_config.SCORING_BENCHMARK_INDUSTRY or None)
        tier = str(sig.get("tier") or "cold")
        lead["opportunity_insight"] = str(sig.get("reason") or sig.get("explanation") or "")[:2000]
        oll = _enrich_lead_ollama_pack(lead, model_family=model_family)

        name = str(lead.get("full_name") or "").strip()
        rec = {
            "name": name,
            "title": str(lead.get("title") or "").strip(),
            "company": str(lead.get("company_name") or "").strip(),
            "location": str(lead.get("location") or "").strip(),
            "linkedin_url": str(lead.get("linkedin_url") or "").strip(),
            "website": str(lead.get("company_website") or "").strip(),
            "score": float(sig.get("score") or 0),
            "category": tier_label(tier),
            "company_summary": str(oll.get("short_summary") or "").strip(),
            "pain_points": str(oll.get("pain_points") or "").strip(),
            "opportunity_insight": str(lead.get("opportunity_insight") or "").strip(),
            "linkedin_message": str(oll.get("linkedin_message") or "").strip(),
            "email_message": str(oll.get("email_message") or "").strip(),
            "followup_message": str(oll.get("followup_message") or "").strip(),
            "message": str(oll.get("linkedin_message") or "").strip(),
        }
        final_enriched.append(rec)
        queue.append(
            {
                "name": name,
                "title": str(lead.get("title") or "").strip(),
                "company": str(lead.get("company_name") or "").strip(),
                "location": str(lead.get("location") or "").strip(),
                "linkedin_url": rec["linkedin_url"],
                "message": rec["message"],
                "email_message": rec["email_message"],
                "followup_message": rec["followup_message"],
                "status": "New",
                "score": rec["score"],
                "category": rec["category"],
                "lead_key": rec["linkedin_url"],
            }
        )

    enr_path = os.path.join(out_dir, "enriched_leads.csv")
    qpath = os.path.join(out_dir, "outreach_queue.csv")

    if final_enriched:
        pd.DataFrame(
            [{k: row.get(k, "") for k in _ENRICHED_CSV_COLS} for row in final_enriched]
        ).to_csv(enr_path, index=False)
    else:
        pd.DataFrame(columns=_ENRICHED_CSV_COLS).to_csv(enr_path, index=False)

    if queue:
        pd.DataFrame(
            [{k: row.get(k, "") for k in _QUEUE_CSV_COLS} for row in queue]
        ).to_csv(qpath, index=False)
    else:
        pd.DataFrame(columns=_QUEUE_CSV_COLS).to_csv(qpath, index=False)

    # SQLite (append this run; tables created on first use)
    raw_for_sql: List[Dict[str, Any]] = []
    if os.path.isfile(raw_p) and os.path.getsize(raw_p) > 0:
        rdf = pd.read_csv(raw_p, dtype=str, keep_default_na=False)
        for z in rdf.to_dict(orient="records"):
            raw_for_sql.append(
                {
                    "name": str(z.get("full_name") or z.get("name") or ""),
                    "title": str(z.get("title") or ""),
                    "company": str(z.get("company_name") or ""),
                    "location": str(z.get("location") or ""),
                    "linkedin_url": str(z.get("linkedin_url") or ""),
                }
            )

    if not final_enriched and not raw_for_sql and not err:
        logger.warning("No leads in pipeline (empty search or not logged in).")

    try:
        sqlite_p = save_pipeline_run(
            run_id=run_id,
            raw_rows=raw_for_sql,
            enriched_rows=final_enriched,
            queue_rows=queue,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Pipeline SQLite: %s", e)
        err.append(f"sqlite: {e}")
        sqlite_p = os.path.abspath(app_config.SQLITE_DB_PATH)

    return PipelineResult(
        run_id=run_id,
        exports_dir=out_dir,
        scrape=scrape,
        raw_leads_path=raw_p,
        enriched_leads_path=enr_path,
        outreach_queue_path=qpath,
        sqlite_path=sqlite_p,
        lead_count=len(final_enriched),
        errors=err,
    )
