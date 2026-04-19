"""
Export all safe-captured leads from SQLite to the configured CSV path.

Used by ``run.bat`` menu option 3. Does not change capture or scoring logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # noqa: E402
from database.safe_capture_store import fetch_all_leads, init_safe_capture_db  # noqa: E402


def _missing_deps_message(exc: BaseException) -> None:
    print(
        "Missing dependency for CSV export (pandas is required).\n"
        "From the repository root run:\n"
        "  python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    print(exc, file=sys.stderr)


def main() -> None:
    try:
        from exports.safe_capture_csv_export import leads_to_export_dataframe
    except ImportError as e:
        _missing_deps_message(e)
        sys.exit(1)

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


if __name__ == "__main__":
    main()
