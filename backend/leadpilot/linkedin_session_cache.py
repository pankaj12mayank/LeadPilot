"""
Track LinkedIn session validity metadata for global session control.

The real session is Chrome's user profile (``CHROME_USER_DATA_DIR`` or the profile used with
``--user-data-dir`` on port 9222). This file only stores *metadata* (session_created_at), never credentials.

Default policy: **7 days** (``LEADPILOT_LINKEDIN_SESSION_DAYS``) — about once per week, open
LinkedIn and sign in if the site asks. For a longer window (e.g. ~7 weeks), set e.g. ``49``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_CACHE_NAME = "linkedin_session_cache.json"


def _policy_days() -> int:
    try:
        import config

        d = int(getattr(config, "LEADPILOT_LINKEDIN_SESSION_DAYS", 7) or 7)
    except Exception:
        d = int(os.environ.get("LEADPILOT_LINKEDIN_SESSION_DAYS", "7") or "7")
    return max(1, min(d, 365))


def _cache_path() -> Path:
    try:
        import config

        root = Path(config._REPO_ROOT)
        sub = (getattr(config, "SESSIONS_DIR", "sessions") or "sessions").strip() or "sessions"
    except Exception:
        root = _REPO
        sub = (os.environ.get("SESSIONS_DIR", "sessions") or "sessions").strip() or "sessions"
    return root / sub / _CACHE_NAME


def _ensure_parent(path: Path) -> None:
    try:
        import config

        config.ensure_data_dirs()
    except Exception:
        path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class LinkedinSessionInfo:
    policy_days: int
    session_created_at: str | None
    last_verified_at: str | None
    age_days: float | None
    within_policy: bool
    has_cache: bool
    message: str


def read_cache_raw() -> dict[str, Any] | None:
    p = _cache_path()
    if not p.is_file():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def get_linkedin_session_info() -> LinkedinSessionInfo:
    pol = _policy_days()
    raw = read_cache_raw()
    if not raw:
        return LinkedinSessionInfo(
            policy_days=pol,
            session_created_at=None,
            last_verified_at=None,
            age_days=None,
            within_policy=False,
            has_cache=False,
            message=(
                f"No session file found. Manual LinkedIn login is required before LinkedIn tasks "
                f"(session policy: {pol} day(s))."
            ),
        )
    at = (raw.get("session_created_at") or raw.get("last_verified_at") or raw.get("verified_at") or "").strip()
    if not at:
        return LinkedinSessionInfo(
            policy_days=pol,
            session_created_at=None,
            last_verified_at=None,
            age_days=None,
            within_policy=False,
            has_cache=True,
            message="Session file present but missing session_created_at.",
        )
    try:
        dt = datetime.fromisoformat(at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        return LinkedinSessionInfo(
            policy_days=pol,
            session_created_at=at,
            last_verified_at=at,
            age_days=None,
            within_policy=False,
            has_cache=True,
            message="Could not parse session_created_at.",
        )
    now = datetime.now(timezone.utc)
    age = (now - dt).total_seconds() / 86400.0
    ok = age <= float(pol)
    if ok:
        msg = f"Session valid: created {age:.1f} day(s) ago (policy: {pol} day(s))."
    else:
        msg = (
            f"Session expired: {age:.0f} day(s) old (policy: {pol} day(s)). "
            "Complete manual LinkedIn login, then continue."
        )
    return LinkedinSessionInfo(
        policy_days=pol,
        session_created_at=at,
        last_verified_at=at,
        age_days=age,
        within_policy=ok,
        has_cache=True,
        message=msg,
    )


def touch_linkedin_session_ok() -> None:
    """Update session_created_at after manual login confirmation or successful run."""
    p = _cache_path()
    _ensure_parent(p)
    payload = {
        "session_created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "last_verified_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "version": 1,
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def print_session_status_at_start() -> None:
    """Log once when starting collection (Selenium)."""
    info = get_linkedin_session_info()
    pol = _policy_days()
    print(
        f"\n  [LinkedIn session] Policy: session valid for {pol} day(s) from session_created_at "
        f"(set LEADPILOT_LINKEDIN_SESSION_DAYS; use 49 for ~7 weeks).\n  [LinkedIn session] {info.message}\n",
        flush=True,
    )
    if not info.within_policy:
        print(
            "  [LinkedIn session] LinkedIn tasks should pause now for manual login. Cookies live only in your Chrome profile.\n",
            flush=True,
        )


def session_info_dict() -> dict[str, Any]:
    """For FastAPI / JSON (selenium status)."""
    i = get_linkedin_session_info()
    return {
        "policy_days": i.policy_days,
        "session_created_at": i.session_created_at,
        "last_verified_at": i.last_verified_at,
        "age_days": None if i.age_days is None else round(i.age_days, 2),
        "within_policy": i.within_policy,
        "has_cache": i.has_cache,
        "message": i.message,
    }
