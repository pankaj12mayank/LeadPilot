"""Start/stop the Selenium ``backend.leadpilot`` CLI from the web app (background subprocess)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.api.deps import get_current_user
from backend.leadpilot.linkedin_session_cache import session_info_dict
from backend.services.selenium_leadpilot_process import (
    get_status,
    is_available,
    start_leadpilot_subprocess,
    stop_leadpilot,
)
import config as app_config

router = APIRouter(prefix="/scraper/selenium-leadpilot", tags=["scraper"])


class SeleniumLeadpilotStartBody(BaseModel):
    """Mirrors common ``python -m backend.leadpilot`` flags."""

    max_leads: int | None = Field(default=None, ge=1, le=500)
    test: bool = Field(default=False, description="LEADPILOT_TEST: cap 10 leads")
    skip_enrich: bool = False
    skip_scoring: bool = False
    output: str | None = Field(default=None, description="Output .xlsx path (repo-relative or absolute)")
    lnn_base_url: str | None = Field(
        default=None,
        description="Override LNN_BASE_URL for this run (default: this API, from request + API_ROOT_PATH).",
    )
    skip_preflight: bool = Field(
        default=False,
        description="Set SKIP_PREFLIGHT=1 (not recommended).",
    )


def _default_lnn_url(request: Request) -> str:
    root = (app_config.API_ROOT_PATH or "").rstrip("/")
    if not root.startswith("/"):
        root = "/" + root
    # Same host the browser used to call the API is a good default for the child process on this machine
    base = str(request.base_url).rstrip("/")
    return f"{base}{root}"


@router.get("/status")
def selenium_leadpilot_status(
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    st = get_status()
    out: dict[str, Any] = {**asdict(st), "available": st.available and is_available()}
    try:
        out["linkedin_session"] = session_info_dict()
    except Exception:  # noqa: BLE001
        out["linkedin_session"] = {"message": "Session info unavailable", "has_cache": False}
    return out


@router.post("/start")
def selenium_leadpilot_start(
    request: Request,
    body: SeleniumLeadpilotStartBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not is_available():
        raise HTTPException(
            status_code=503,
            detail="Selenium leadpilot is not available (missing backend/leadpilot).",
        )

    argv: list[str] = ["-m", "backend.leadpilot"]
    if body.test:
        argv.append("--test")
    if body.max_leads is not None:
        argv.extend(["-n", str(body.max_leads)])
    if body.skip_enrich:
        argv.append("--skip-enrich")
    if body.skip_scoring:
        argv.append("--skip-scoring")
    if body.output:
        argv.extend(["-o", body.output])

    extra: dict[str, str] = {}
    lnn = (body.lnn_base_url or "").strip() or _default_lnn_url(request)
    extra["LNN_BASE_URL"] = lnn
    if body.skip_preflight:
        extra["SKIP_PREFLIGHT"] = "1"
    if body.test:
        extra["LEADPILOT_TEST"] = "1"
        extra.setdefault("DEBUG", "1")
    # Web UI has no TTY: timed waits instead of "Press Enter".
    extra["LEADPILOT_SKIP_READY_PROMPT"] = "1"
    # Give time to open Chrome and log in before the *second* wait (search + start capture).
    extra.setdefault("LEADPILOT_READY_DELAY_SECONDS", "60")
    # After login, user must run People search; then this delay before we read /in/ links (no TTY to press Enter).
    extra.setdefault("LEADPILOT_START_CAPTURE_DELAY_SECONDS", "120")
    extra["LEADPILOT_SKIP_START_CAPTURE_PROMPT"] = "1"
    # Do not auto-open a default search page; start on feed, user searches manually, then capture starts.
    extra.setdefault("LEADPILOT_OPEN_PEOPLE_ON_LAUNCH", "0")
    extra.setdefault("LEADPILOT_AUTO_OPEN_PEOPLE_SEARCH", "0")

    err = start_leadpilot_subprocess(argv=argv, extra_env=extra)
    if err:
        if "already" in err.lower():
            raise HTTPException(status_code=409, detail=err)
        raise HTTPException(status_code=500, detail=err)
    st = get_status()
    return {"ok": True, "status": asdict(st)}


@router.post("/stop")
def selenium_leadpilot_stop(
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    err = stop_leadpilot()
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"ok": True, "status": asdict(get_status())}
