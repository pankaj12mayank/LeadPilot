from __future__ import annotations

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from database.meta_db import meta_db_path
from database.orm.base import Base

import database.orm.models  # noqa: F401 — register models on Base.metadata

_engine = None
SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        path = meta_db_path()
        _engine = create_engine(
            f"sqlite:///{path}",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_engine, "connect")
        def _sqlite_pragma(dbapi_connection, _connection_record) -> None:  # type: ignore[no-redef]
            cur = dbapi_connection.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return _engine


def _ensure_lead_indexes(engine) -> None:
    """Add query indexes on existing SQLite DBs (CREATE INDEX IF NOT EXISTS)."""
    stmts = [
        "CREATE INDEX IF NOT EXISTS ix_leads_email ON leads (email)",
        "CREATE INDEX IF NOT EXISTS ix_leads_company_name ON leads (company_name)",
        "CREATE INDEX IF NOT EXISTS ix_leads_score ON leads (score)",
        "CREATE INDEX IF NOT EXISTS ix_leads_created_at ON leads (created_at)",
    ]
    with engine.begin() as cx:
        for sql in stmts:
            cx.execute(text(sql))


def _ensure_lead_columns(engine) -> None:
    """SQLite lightweight migrations for ``leads`` (ADD COLUMN if missing)."""
    with engine.begin() as cx:
        cur = cx.execute(text("PRAGMA table_info(leads)"))
        cols = {row[1] for row in cur.fetchall()}
        if "last_contacted_at" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN last_contacted_at VARCHAR(64) DEFAULT ''"))
        if "follow_up_reminder_at" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN follow_up_reminder_at VARCHAR(64) DEFAULT ''"))


def init_sa_tables() -> None:
    """Create SQLAlchemy-managed tables if missing (SQLite)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _ensure_lead_columns(engine)
    _ensure_lead_indexes(engine)


def get_session_factory():
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return SessionLocal
