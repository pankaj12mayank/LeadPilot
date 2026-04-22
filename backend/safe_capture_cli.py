"""CLI entry for the safe manual capture pipeline and SQLite → CSV export."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend.safe_capture_orchestrator import print_preflight, run_interactive_capture


def _run_export() -> None:
    try:
        from exports.safe_capture_csv_export import leads_to_export_dataframe
    except ImportError as e:
        print(
            "Missing dependency for CSV export (pandas is required).\n"
            "From the repository root run:  python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        print(e, file=sys.stderr)
        raise SystemExit(1) from e

    import config
    from database.safe_capture_store import fetch_all_leads, init_safe_capture_db

    config.ensure_data_dirs()
    init_safe_capture_db()
    rows = fetch_all_leads()
    if not rows:
        print("No leads in the database; nothing to export.")
        print(f"DB: {config.SAFE_CAPTURE_DB_PATH}")
        return

    df = leads_to_export_dataframe(rows)
    path = Path(config.SAFE_CAPTURE_CSV_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Exported {len(df)} row(s) to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LeadPilot safe manual capture (one lead at a time, synchronous Playwright)."
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="capture",
        choices=("capture", "paths", "export"),
        help="capture: interactive session; paths: print storage paths; export: SQLite → CSV",
    )
    parser.add_argument(
        "--url",
        dest="start_url",
        default=None,
        help="Optional first URL to open (you still browse manually afterwards).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Headless browser (not recommended for manual login).",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Skip CSV append (SQLite insert still runs).",
    )
    args = parser.parse_args()

    if args.action == "paths":
        print_preflight()
        return

    if args.action == "export":
        _run_export()
        return

    run_interactive_capture(
        start_url=args.start_url,
        headless=bool(args.headless),
        skip_export_csv=bool(args.no_csv),
    )


if __name__ == "__main__":
    main()
