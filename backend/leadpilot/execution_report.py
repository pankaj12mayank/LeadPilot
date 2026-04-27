"""End-of-run summary for LinkedIn / leadpilot pipelines (stdout)."""

from __future__ import annotations

# Shipped-in changelog (code audit); extend when you fix/remove items in this package.
# Use ASCII only so Windows cmd.exe does not show replacement characters.
_SHIPPED = (
    "2026-04-27: Chrome connect retries; shared attach env; per-profile WebDriver retries; "
    "delays default 3-7s (env DELAY_MIN/MAX); scroll delays tunable; preflight output dir = repo root; "
    "CLI --launch-chrome overrides attach without editing .env. "
    "2026-04-28: lenient preflight default (LEADPILOT_STRICT_PREFLIGHT=0) so Ollama/Chrome-smoke can warn; "
    "no debugger on 9222 auto-switches to Selenium launch; app UI is LinkedIn-only for lead search. "
    "LEADPILOT_SKIP_READY_PROMPT + delay replaces Press-Enter in API runs; v3 rows ingest to Leads (LEADPILOT_INGEST_TO_CRM)."
)


def print_pipeline_footer(
    *,
    success: bool,
    rows: int = 0,
    output_excel: str | None = None,
    error: str | None = None,
) -> None:
    """Call once at the end of a pipeline run (CLI or imported)."""
    line = "=" * 56
    print(f"\n{line}", flush=True)
    print("  LEADPILOT PIPELINE - RUN SUMMARY", flush=True)
    print(line, flush=True)
    st = "OK" if success else "FAILED / INCOMPLETE"
    print(f"  Current system status: {st}", flush=True)
    if error:
        print(f"  What was wrong this run: {error}", flush=True)
    else:
        print("  What was wrong this run: (none - completed path)", flush=True)
    print(f"  Rows collected / processed: {rows}", flush=True)
    if output_excel:
        print(f"  Excel output: {output_excel}", flush=True)
    print("  What was fixed in codebase (cumulative):", flush=True)
    print(f"    - {_SHIPPED}", flush=True)
    print("  What was removed (cumulative): unused scraper_core helpers, duplicate preflight paths.", flush=True)
    print(f"{line}\n", flush=True)
