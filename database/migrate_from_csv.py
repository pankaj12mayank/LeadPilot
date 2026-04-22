"""
Import leads from CSV storage into SQLite (normalized).

Callable from code or: python -m database.migrate_from_csv
"""

from __future__ import annotations

import config
from backend.settings.lead_schema import normalize_lead_row
from backend.storage.csv_storage import CsvStorage
from backend.storage.sqlite_storage import SqliteStorage


def migrate(csv_path: str | None = None, db_path: str | None = None) -> int:
    csv_storage = CsvStorage(csv_path or config.CSV_FILE_PATH)
    sqlite_storage = SqliteStorage(db_path or getattr(config, "SQLITE_DB_PATH", "database/leads.db"))
    sqlite_storage.init_storage()
    leads = csv_storage.list_leads()
    sqlite_storage.sync_leads([normalize_lead_row(x) for x in leads])
    return len(leads)


if __name__ == "__main__":
    n = migrate()
    print(f"Migrated {n} lead(s).")
