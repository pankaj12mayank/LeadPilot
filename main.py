"""
LeadPilot single-run CLI: LinkedIn (Playwright) -> clean -> score -> Ollama -> CSV + SQLite.

Usage (from Leadpilot repo root)::

    python main.py --keyword "software engineer" --country "United States" --max-leads 20

Requires a logged-in LinkedIn session under ``sessions/playwright_user_data/linkedin/``
(created automatically on first run via a headed browser window).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)

from backend.pipeline.lead_pipeline import PipelineResult, run_linkedin_lead_pipeline  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LinkedIn-only lead pipeline (Playwright + Ollama).")
    p.add_argument("--keyword", "-k", default="", help="Search keywords (role, skills, etc.)")
    p.add_argument("--country", "-c", default="", help="Location / region (folded into LinkedIn keywords)")
    p.add_argument("--industry", default="", help="Industry filter (folded into keywords)")
    p.add_argument("--company-size", default="", help="Company size hint (folded into keywords)")
    p.add_argument(
        "--max-leads",
        "-n",
        type=int,
        default=None,
        help="Max leads to collect (1–50, default from env SCRAPER_MAX_LEADS_DEFAULT)",
    )
    p.add_argument(
        "--exports-dir",
        default="",
        help="Output directory for CSV files (default: EXPORTS_DIR from config, usually ./exports)",
    )
    p.add_argument("--headless", action="store_true", help="Run browser headless (not recommended for first login)")
    p.add_argument(
        "--no-manual-login",
        action="store_true",
        help="Do not open a login window (use only if session already verified)",
    )
    p.add_argument(
        "--login-wait-seconds",
        type=int,
        default=None,
        help="How long to keep the manual login window open (default: SCRAPER_MANUAL_LOGIN_DEFAULT_SECONDS)",
    )
    p.add_argument(
        "--profile-contact-enrich",
        action="store_true",
        help="Open a few profile pages to pick up public mailto/tel (capped in config)",
    )
    p.add_argument(
        "--model",
        default="llama3",
        help="Ollama model family for message pack: llama3 | mistral | deepseek",
    )
    return p.parse_args()


def _print_summary(r: PipelineResult) -> None:
    print("")
    print("========== Lead pipeline summary ==========")
    print(f"  run_id:        {r.run_id}")
    print(f"  exports:       {r.exports_dir}")
    print(f"  raw_leads:     {r.raw_leads_path}")
    print(f"  enriched:      {r.enriched_leads_path}")
    print(f"  outreach:      {r.outreach_queue_path}")
    print(f"  sqlite:        {r.sqlite_path}")
    print(f"  leads (final): {r.lead_count}")
    print(f"  scrape saved:  {r.scrape.saved}  (run {r.scrape.run_id})")
    if r.scrape.errors:
        print("  scrape notes:")
        for e in r.scrape.errors:
            print(f"    - {e}")
    if r.errors:
        print("  pipeline notes:")
        for e in r.errors:
            print(f"    - {e}")
    print("==========================================")
    print("")


def main() -> None:
    args = _parse_args()
    if not (args.keyword or args.country or args.industry or args.company_size):
        print("Error: pass at least one of --keyword, --country, --industry, or --company-size.", file=sys.stderr)
        sys.exit(2)
    res = run_linkedin_lead_pipeline(
        keyword=args.keyword,
        country=args.country,
        industry=args.industry,
        company_size=args.company_size or "",
        max_leads=args.max_leads,
        exports_dir=args.exports_dir or None,
        model_family=str(args.model or "llama3"),
        headless=bool(args.headless),
        profile_contact_enrich=bool(args.profile_contact_enrich),
        require_manual_login=not bool(args.no_manual_login),
        manual_login_wait_seconds=args.login_wait_seconds,
    )
    _print_summary(res)
    sys.exit(0 if not res.errors else 1)


if __name__ == "__main__":
    main()
