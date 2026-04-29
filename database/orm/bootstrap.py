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
            connect_args={"check_same_thread": False, "timeout": 30.0},
        )

        @event.listens_for(_engine, "connect")
        def _sqlite_pragma(dbapi_connection, _connection_record) -> None:  # type: ignore[no-redef]
            cur = dbapi_connection.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.close()

    return _engine


def _ensure_lead_indexes(engine) -> None:
    """Add query indexes on existing SQLite DBs (CREATE INDEX IF NOT EXISTS)."""
    stmts = [
        "CREATE INDEX IF NOT EXISTS ix_leads_email ON leads (email)",
        "CREATE INDEX IF NOT EXISTS ix_leads_company_name ON leads (company_name)",
        "CREATE INDEX IF NOT EXISTS ix_leads_score ON leads (score)",
        "CREATE INDEX IF NOT EXISTS ix_leads_created_at ON leads (created_at)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_companies_domain ON companies (domain)",
        "CREATE INDEX IF NOT EXISTS ix_companies_company_name ON companies (company_name)",
        "CREATE INDEX IF NOT EXISTS ix_companies_last_updated ON companies (last_updated)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_company_enrichment_company_id ON company_enrichment (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_company_enrichment_last_checked ON company_enrichment (last_checked)",
        "CREATE INDEX IF NOT EXISTS ix_company_enrichment_score ON company_enrichment (score)",
        "CREATE INDEX IF NOT EXISTS ix_company_enrichment_priority ON company_enrichment (priority)",
        "CREATE INDEX IF NOT EXISTS ix_leads_priority ON leads (priority)",
        "CREATE INDEX IF NOT EXISTS ix_leads_user_id ON leads (user_id)",
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
        if "agency_type" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN agency_type VARCHAR(128) DEFAULT ''"))
        if "problem_seen" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN problem_seen TEXT DEFAULT ''"))
        if "last_active_display" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN last_active_display VARCHAR(255) DEFAULT ''"))
        if "connection_sent" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN connection_sent VARCHAR(128) DEFAULT ''"))
        if "replied_yn" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN replied_yn VARCHAR(8) DEFAULT 'N'"))
        if "solution_text" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN solution_text TEXT DEFAULT ''"))
        if "signal_hiring" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN signal_hiring INTEGER NOT NULL DEFAULT 0"))
        if "signal_scaling" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN signal_scaling INTEGER NOT NULL DEFAULT 0"))
        if "signal_content_gap" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN signal_content_gap INTEGER NOT NULL DEFAULT 0"))
        if "signal_ads_gap" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN signal_ads_gap INTEGER NOT NULL DEFAULT 0"))
        if "priority" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN priority VARCHAR(16) DEFAULT 'Cold'"))
        if "user_id" not in cols:
            cx.execute(text("ALTER TABLE leads ADD COLUMN user_id VARCHAR(36) NOT NULL DEFAULT ''"))


def _ensure_user_columns(engine) -> None:
    """SQLite migrations for ``users`` (additive columns)."""
    with engine.begin() as cx:
        cur = cx.execute(text("PRAGMA table_info(users)"))
        cols = {row[1] for row in cur.fetchall()}
        if not cols:
            return
        if "is_active" not in cols:
            cx.execute(text("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"))
        if "role" not in cols:
            cx.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'user'"))
        if "plan_id" not in cols:
            cx.execute(text("ALTER TABLE users ADD COLUMN plan_id VARCHAR(32) NOT NULL DEFAULT 'starter'"))
        if "last_login_at" not in cols:
            cx.execute(text("ALTER TABLE users ADD COLUMN last_login_at VARCHAR(64) DEFAULT ''"))


def _ensure_company_enrichment_columns(engine) -> None:
    """SQLite migrations for ``company_enrichment`` (additive columns)."""
    with engine.begin() as cx:
        cur = cx.execute(text("PRAGMA table_info(company_enrichment)"))
        cols = {row[1] for row in cur.fetchall()}
        if not cols:
            return
        if "signal_hiring" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN signal_hiring INTEGER NOT NULL DEFAULT 0"))
        if "signal_scaling" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN signal_scaling INTEGER NOT NULL DEFAULT 0"))
        if "signal_content_gap" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN signal_content_gap INTEGER NOT NULL DEFAULT 0"))
        if "signal_ads_gap" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN signal_ads_gap INTEGER NOT NULL DEFAULT 0"))
        if "score" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN score REAL DEFAULT 0"))
        if "priority" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN priority VARCHAR(16) DEFAULT 'Cold'"))
        if "ai_summary" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN ai_summary TEXT DEFAULT ''"))
        if "ai_problems" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN ai_problems TEXT DEFAULT ''"))
        if "ai_opportunity" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN ai_opportunity TEXT DEFAULT ''"))
        if "ai_score" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN ai_score REAL DEFAULT 0"))
        if "ai_provider" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN ai_provider VARCHAR(32) DEFAULT ''"))
        if "ai_cache_key" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN ai_cache_key VARCHAR(64) DEFAULT ''"))
        if "ai_updated_at" not in cols:
            cx.execute(text("ALTER TABLE company_enrichment ADD COLUMN ai_updated_at VARCHAR(64) DEFAULT ''"))


def _ensure_company_columns(engine) -> None:
    """SQLite migrations for ``companies`` (additive columns)."""
    with engine.begin() as cx:
        cur = cx.execute(text("PRAGMA table_info(companies)"))
        cols = {row[1] for row in cur.fetchall()}
        if not cols:
            return
        if "signals" not in cols:
            cx.execute(text("ALTER TABLE companies ADD COLUMN signals TEXT DEFAULT ''"))
        if "ai_score" not in cols:
            cx.execute(text("ALTER TABLE companies ADD COLUMN ai_score REAL DEFAULT 0"))


def init_sa_tables() -> None:
    """Create SQLAlchemy-managed tables if missing (SQLite)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _ensure_lead_columns(engine)
    _ensure_user_columns(engine)
    _ensure_company_columns(engine)
    _ensure_company_enrichment_columns(engine)
    _ensure_lead_indexes(engine)


def get_session_factory():
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return SessionLocal
