"""Orchestrate one-shot manual lead capture (single lead, synchronous Playwright)."""

from __future__ import annotations

import json
import sys
from typing import Any

import config
from connectors.capture_router import parse_lead_from_snapshot
from connectors.dom_snapshot import snapshot_visible_page
from database.safe_capture_store import init_safe_capture_db, insert_captured_lead
from exports.safe_capture_csv_export import append_lead_row
from modules.capture_enrich import enrich_lead
from modules.capture_normalize import normalize_parsed_lead
from modules.capture_score import score_lead
from services.capture_browser import CaptureBrowser, launch_capture_browser
from utils.capture_lock import CaptureLock
from utils.platform_detect import detect_platform_from_url
from utils.safe_capture_logging import get_safe_capture_logger

_log = get_safe_capture_logger("orchestrator")


def _pick_active_page(browser: CaptureBrowser):
    ctx = browser.context
    pages = ctx.pages
    if not pages:
        return ctx.new_page()
    return pages[-1]


def run_interactive_capture(
    *,
    start_url: str | None = None,
    headless: bool = False,
    skip_export_csv: bool = False,
) -> dict[str, Any]:
    """
    Open a persistent browser, wait for the operator, then capture **exactly one** lead.

    Raises ``RuntimeError`` if a capture lock cannot be acquired.
    """
    config.ensure_data_dirs()
    init_safe_capture_db()

    with CaptureLock(config.SAFE_CAPTURE_LOCK_PATH):
        browser = launch_capture_browser(headless=headless)
        captured_at = ""
        try:
            page = _pick_active_page(browser)
            if start_url:
                _log.info("Opening start URL (manual browsing afterwards).")
                page.goto(start_url, wait_until="domcontentloaded")

            print(
                "\n=== LeadPilot — Safe manual capture ===\n"
                "1) Log in manually if needed (LinkedIn, Apollo, etc.).\n"
                "2) Search and open **one** lead profile in this window.\n"
                "3) Return here and press **Enter** to capture the **visible** page.\n"
                "   (No auto-scroll, no bulk actions, one lead at a time.)\n",
                flush=True,
            )
            try:
                input("Press Enter when the lead page is visible… ")
            except EOFError:
                raise SystemExit("stdin closed — cannot capture interactively.")

            page = _pick_active_page(browser)
            snap = snapshot_visible_page(page)
            platform = detect_platform_from_url(str(snap.get("url") or page.url))
            _log.info("Detected platform=%s url=%s", platform, snap.get("url"))

            raw = parse_lead_from_snapshot(platform, snap)
            lead = normalize_parsed_lead(raw, platform)
            text_sample = str(snap.get("textSample") or "")
            lead, enrich_meta = enrich_lead(lead, text_sample)
            score, tier = score_lead(lead, enrich_meta)
            lead["score"] = score
            lead["tier"] = tier

            if not str(lead.get("profile_url") or "").strip():
                raise RuntimeError("Missing profile URL — cannot persist lead.")

            row_id, captured_at = insert_captured_lead(lead, enrich_meta)

            if not skip_export_csv:
                append_lead_row(lead, captured_at)

            summary = {
                "id": row_id,
                "platform": platform,
                "score": score,
                "tier": tier,
                "profile_url": lead.get("profile_url"),
                "name": lead.get("name"),
                "company": lead.get("company"),
            }
            _log.info("Captured lead id=%s summary=%s", row_id, json.dumps(summary))
            print("\nSaved lead:", json.dumps(summary, indent=2), "\n", flush=True)
            return summary
        except Exception:
            _log.exception("Capture failed")
            raise
        finally:
            browser.close()


def print_preflight() -> None:
    print("Python:", sys.version.split()[0], flush=True)
    print("DB path:", config.SAFE_CAPTURE_DB_PATH, flush=True)
    print("CSV path:", config.SAFE_CAPTURE_CSV_PATH, flush=True)
    print("Profile dir:", config.SAFE_CAPTURE_PROFILE_DIR, flush=True)
