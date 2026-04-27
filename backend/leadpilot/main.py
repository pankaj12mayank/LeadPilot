"""
LeadPilot v3 — orchestrate: LinkedIn -> enrich (Apollo/Skrapp) -> score -> export.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Repository root (where config.py, .env, exports live)
_ROOT = Path(__file__).resolve().parents[2]

from .enrichment import (
    EnrichmentResult,
    enrich_batch,
    merge_enrichment,
)
from .export import export_leadpilot
from .execution_report import print_pipeline_footer
from .preflight import run_verification
from .scoring import apply_scoring
from .scraper import scrape_for_leads
from .utils import env_bool, get_logger

log = get_logger("leadpilot.main")


def _apply_test_mode_cap(n: int | None) -> int | None:
    if (os.environ.get("LEADPILOT_TEST") or "").strip() in ("1", "true", "True"):
        cap = 10
        if n is None:
            return cap
        return min(n, cap)
    return n


def run_pipeline(
    max_leads: int | None,
    *,
    ask_lead_limit: bool = False,
    skip_enrich: bool = False,
    skip_scoring: bool = False,
    json_out: str | None = None,
    xlsx_out: str | None = None,
) -> list[dict]:
    max_leads = _apply_test_mode_cap(max_leads)
    if env_bool("DEBUG", False):
        log.setLevel(10)
        log.debug("DEBUG=True")

    if env_bool("LEADPILOT_PREFLIGHT", True) and not env_bool(
        "SKIP_PREFLIGHT", False
    ):
        if not run_verification():
            log.error("Preflight failed")
            print_pipeline_footer(
                success=False,
                error="Preflight failed — fix checks above or set SKIP_PREFLIGHT=1.",
                rows=0,
            )
            sys.exit(1)

    log.info("Starting LinkedIn collection...")
    raw = scrape_for_leads(max_leads, ask_limit=ask_lead_limit)
    if not raw:
        log.error("No rows from LinkedIn step")
        print_pipeline_footer(
            success=False,
            error="No rows from LinkedIn (search page empty, locked profiles, or errors).",
            rows=0,
        )
        return []

    if skip_enrich or os.environ.get("ENRICHMENT_ENABLED", "1") == "0":
        skip = EnrichmentResult(
            status="skipped_config", source="none", raw_note="enrichment off"
        )
        enriched = [merge_enrichment(r, skip) for r in raw]
    else:
        log.info("Enriching %s leads (Apollo -> Skrapp fallback)...", len(raw))
        pairs = enrich_batch(raw)
        enriched = [merge_enrichment(r, e) for r, e in pairs]

    if not skip_scoring:
        log.info("Scoring...")
        scored = [apply_scoring(r) for r in enriched]
    else:
        scored = enriched

    out_x = xlsx_out or os.environ.get(
        "LEADPILOT_OUT_XLSX", str(_ROOT / "leadpilot_runs.xlsx")
    )
    if not out_x.lower().endswith(".xlsx"):
        out_x += ".xlsx"
    try:
        export_leadpilot(scored, out_x, json_path=json_out)
    except OSError as e:
        print_pipeline_footer(
            success=False,
            error=f"Excel export failed: {e!s}",
            rows=len(scored),
            output_excel=out_x,
        )
        raise
    print_pipeline_footer(
        success=True,
        rows=len(scored),
        output_excel=out_x,
    )
    return scored


def _cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="LeadPilot: LinkedIn scrape + enrichment + AI scoring",
    )
    p.add_argument(
        "-n",
        "--max-leads",
        type=int,
        default=None,
        help="Max profiles to collect (overrides .env; combined with LEADPILOT_TEST cap)",
    )
    p.add_argument(
        "--ask",
        action="store_true",
        help="Ask for how many leads after the browser is ready (like lead_scraper ASK_MAX_LEADS)",
    )
    p.add_argument(
        "--skip-enrich", action="store_true", help="Do not call Apollo/Skrapp"
    )
    p.add_argument(
        "--skip-scoring", action="store_true", help="Rule/GPT scoring off"
    )
    p.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output .xlsx path (default: LEADPILOT_OUT_XLSX or leadpilot_runs.xlsx)",
    )
    p.add_argument(
        "--json",
        type=str,
        default=None,
        help="Also write JSON to this path (or set LEADPILOT_EXPORT_JSON=1 with path)",
    )
    p.add_argument(
        "--test", action="store_true", help="LEADPILOT_TEST: cap 10 leads, DEBUG-friendly"
    )
    return p.parse_args()


def main() -> None:
    args = _cli()
    if args.test:
        os.environ["LEADPILOT_TEST"] = "1"
        os.environ.setdefault("DEBUG", "1")
    try:
        run_pipeline(
            args.max_leads,
            ask_lead_limit=args.ask,
            skip_enrich=args.skip_enrich,
            skip_scoring=args.skip_scoring,
            json_out=args.json,
            xlsx_out=args.output,
        )
    except KeyboardInterrupt:
        log.error("Interrupted")
        sys.exit(130)


if __name__ == "__main__":
    main()
