"""Scraper API: manual Playwright login, multi-platform runs, raw export, live job progress."""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import asdict
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.api.deps import get_current_user
from backend.modules.scraper.service import scrape_profile_preview
from backend.scraper.config import ScraperRunConfig, ScraperRunResult
from backend.scraper.exceptions import SessionMissingError, UnsupportedPlatformError
from backend.scraper.progress import create_job, eta_seconds, fail_job, get_job, complete_job
from backend.scraper.registry import list_platform_slugs
from backend.scraper.runner import run_scrape_sync
from backend.scraper.session_manager import SessionManager
from backend.scraper.urls import LOGIN_START_URLS, login_url, supported_platforms
from backend.services import platform_registry_service
from backend.services.platform_channels import active_channel_slugs
import config as app_config

router = APIRouter(prefix="/scraper", tags=["scraper"])


def _resolve_manual_login_url(slug: str) -> str:
    if slug in LOGIN_START_URLS:
        return login_url(slug)
    u = platform_registry_service.get_custom_login_url(slug)
    if u:
        return u
    raise HTTPException(
        status_code=400,
        detail="Add this custom platform with a sign-in URL before connecting.",
    )


def _result_to_public(r: ScraperRunResult) -> Dict[str, Any]:
    return {
        "success": r.success,
        "platform": r.platform,
        "total_found": r.total_found,
        "saved": r.saved,
        "duplicates_removed": r.duplicates_removed,
        "csv_file": r.csv_file,
        "run_id": r.run_id,
        "errors": r.errors,
    }


class ScrapePreviewBody(BaseModel):
    url: str = Field(..., min_length=4)
    platform: str = Field(default="linkedin", max_length=64)


class ManualLoginBody(BaseModel):
    """How long to keep the headed browser open for the user to complete login."""

    wait_seconds: int = Field(default=180, ge=30, le=1200)


class ScraperRunBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    platform: str = Field(..., min_length=2, max_length=64)
    keyword: str = Field(..., min_length=1, max_length=500)
    country: str = ""
    industry: str = ""
    company_size: str = ""
    max_leads: int = Field(default=20, ge=1, le=50)
    lead_limit: int | None = Field(None, ge=1, le=50)
    headless: bool = True
    delay_min_seconds: float = Field(default=3.0, ge=1.0, le=10.0)
    delay_max_seconds: float = Field(default=5.0, ge=1.0, le=10.0)
    max_scroll_rounds: int = Field(default=12, ge=1, le=40)
    """When true, returns 202 + ``job_id``; poll ``GET /scraper/jobs/{job_id}`` for live status."""

    async_job: bool = False
    profile_contact_enrich: bool = Field(
        default=False,
        description="LinkedIn: after search, open profiles to capture public mailto/tel when visible (slower).",
    )

    @model_validator(mode="after")
    def _lead_limit_alias(self) -> "ScraperRunBody":
        if self.lead_limit is not None:
            self.max_leads = int(self.lead_limit)
        return self


def _cfg_from_body(body: ScraperRunBody) -> ScraperRunConfig:
    return ScraperRunConfig(
        platform=body.platform,
        keyword=body.keyword,
        country=body.country,
        industry=body.industry,
        company_size=body.company_size,
        max_leads=body.max_leads,
        delay_min_seconds=body.delay_min_seconds,
        delay_max_seconds=body.delay_max_seconds,
        headless=body.headless,
        max_scroll_rounds=body.max_scroll_rounds,
        profile_contact_enrich=bool(body.profile_contact_enrich),
    )


def _run_job_thread(job_id: str, cfg: ScraperRunConfig) -> None:
    try:
        result = run_scrape_sync(cfg, job_id=job_id)
        complete_job(job_id, _result_to_public(result))
    except SessionMissingError as e:
        fail_job(job_id, str(e))
    except UnsupportedPlatformError as e:
        fail_job(job_id, str(e))
    except ValueError as e:
        fail_job(job_id, str(e))
    except Exception as e:
        fail_job(job_id, str(e))


@router.get("/status")
def scraper_status(_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    return {
        "ok": True,
        "engine": "playwright",
        "platforms": list_platform_slugs(),
        "delay_seconds_range": [
            app_config.SCRAPER_DELAY_MIN_SECONDS,
            app_config.SCRAPER_DELAY_MAX_SECONDS,
        ],
        "max_leads_default": app_config.SCRAPER_MAX_LEADS_DEFAULT,
        "max_leads_cap": app_config.SCRAPER_MAX_LEADS_HARD_CAP,
    }


@router.get("/platforms")
def scraper_platforms(_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    return {"platforms": supported_platforms()}


@router.get("/jobs/{job_id}")
def scraper_job_status(job_id: str, _user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Live progress for an async scrape (phases, page, preview rows, ETA)."""
    st = get_job(job_id)
    if not st:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    base = asdict(st)
    base["eta_seconds"] = eta_seconds(job_id)
    return base


@router.post("/preview")
async def scrape_preview(
    body: ScrapePreviewBody,
    _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    return await scrape_profile_preview(body.url, body.platform)


@router.post("/sessions/{platform}/manual-login")
async def manual_login_window(
    platform: str,
    body: ManualLoginBody,
    _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Open a real browser window; user logs in manually; session is saved under ``sessions/``."""
    slug = platform.strip().lower().replace(" ", "_")
    start = _resolve_manual_login_url(slug)
    try:
        await asyncio.to_thread(
            SessionManager().open_login_window,
            slug,
            int(body.wait_seconds * 1000),
            start,
        )
    except UnsupportedPlatformError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"ok": True, "platform": slug, "wait_seconds": body.wait_seconds}


@router.get("/sessions/{platform}")
def session_exists(platform: str, _user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    slug = platform.strip().lower().replace(" ", "_")
    sm = SessionManager()
    connected = sm.session_connected(slug)
    return {
        "platform": slug,
        "has_session": connected,
        "has_profile": sm.has_session(slug),
        "connected": connected,
        "path": str(sm.path_for(slug)),
    }


@router.post("/sessions/{platform}/verify")
def verify_one_session(platform: str, _user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    from backend.scraper.session_verify import verify_playwright_session

    slug = platform.strip().lower().replace(" ", "_")
    sm = SessionManager()
    ok = verify_playwright_session(slug, custom_login_url=platform_registry_service.get_custom_login_url(slug))
    sm.write_verification(slug, ok, connection_source="probe")
    return {
        "platform": slug,
        "connected": sm.session_connected(slug),
        "probe_ok": ok,
        "has_profile": sm.has_session(slug),
    }


@router.post("/sessions/verify-all")
def verify_all_sessions(_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    from backend.scraper.session_verify import verify_playwright_session

    sm = SessionManager()
    results: Dict[str, Any] = {}
    for slug in active_channel_slugs():
        ok = verify_playwright_session(slug, custom_login_url=platform_registry_service.get_custom_login_url(slug))
        sm.write_verification(slug, ok, connection_source="probe")
        results[slug] = {
            "connected": sm.session_connected(slug),
            "probe_ok": ok,
            "has_profile": sm.has_session(slug),
        }
    return {"ok": True, "results": results}


@router.post("/run")
async def run_scraper(
    body: ScraperRunBody,
    _user: dict = Depends(get_current_user),
) -> Any:
    """
    Keyword search scrape (requires saved session). Raw rows → SQLite + CSV.

    - **Sync** (default): blocks until done; returns ``success``, ``total_found``, ``saved``, etc.
    - **Async** (``async_job: true``): returns **202** with ``job_id``; poll ``GET /scraper/jobs/{job_id}``.
    """
    cfg = _cfg_from_body(body)

    if body.async_job:
        job_id = str(uuid.uuid4())
        d_lo, d_hi = cfg.effective_delays()
        create_job(
            job_id,
            cfg.platform,
            int(cfg.max_leads or 20),
            max_scroll_rounds=int(cfg.max_scroll_rounds),
            delay_avg_seconds=(float(d_lo) + float(d_hi)) / 2.0,
        )
        t = threading.Thread(target=_run_job_thread, args=(job_id, cfg), daemon=True)
        t.start()
        return JSONResponse(
            status_code=202,
            content={
                "accepted": True,
                "job_id": job_id,
                "poll_url": f"/scraper/jobs/{job_id}",
                "platform": cfg.platform,
                "keyword": cfg.keyword,
            },
        )

    try:
        result = await asyncio.to_thread(run_scrape_sync, cfg, None)
    except SessionMissingError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except UnsupportedPlatformError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return _result_to_public(result)
