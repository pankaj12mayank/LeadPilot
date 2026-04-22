#!/usr/bin/env python3
"""Initialize SQLite schema and runtime directories (same steps as API lifespan startup)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from database.meta_db import init_meta_schema  # noqa: E402
from database.orm.bootstrap import init_sa_tables  # noqa: E402
from backend.services import lead_service  # noqa: E402


def main() -> None:
    config.ensure_data_dirs()
    init_meta_schema()
    init_sa_tables()
    lead_service.init_storage()
    print("OK: meta schema, SQLAlchemy tables, storage backend initialized.")
    print(f"  API_META_DB_PATH={config.API_META_DB_PATH}")
    print(f"  STORAGE_MODE={config.STORAGE_MODE}")


if __name__ == "__main__":
    main()
