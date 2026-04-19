"""CLI entry for the safe manual capture pipeline."""

from __future__ import annotations

import argparse

from backend.safe_capture_orchestrator import print_preflight, run_interactive_capture


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LeadPilot safe manual capture (one lead at a time, synchronous Playwright)."
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="capture",
        choices=("capture", "paths"),
        help="capture: interactive session; paths: print resolved storage paths",
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

    run_interactive_capture(
        start_url=args.start_url,
        headless=bool(args.headless),
        skip_export_csv=bool(args.no_csv),
    )


if __name__ == "__main__":
    main()
