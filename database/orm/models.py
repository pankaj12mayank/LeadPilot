"""SQLAlchemy models: users, leads, outreach_history, platform_sessions, app_settings."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.orm.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    last_login_at: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    company_name: Mapped[str] = mapped_column(Text, default="", index=True)
    company_website: Mapped[str] = mapped_column(Text, default="")
    linkedin_url: Mapped[str] = mapped_column(Text, default="")
    email: Mapped[str] = mapped_column(String(320), default="", index=True)
    phone: Mapped[str] = mapped_column(String(64), default="")
    company_size: Mapped[str] = mapped_column(String(64), default="")
    industry: Mapped[str] = mapped_column(String(128), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    source_platform: Mapped[str] = mapped_column(String(64), default="", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    tier: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    personalized_message: Mapped[str] = mapped_column(Text, default="")
    followup_message: Mapped[str] = mapped_column(Text, default="")
    last_contacted_at: Mapped[str] = mapped_column(String(64), default="")
    follow_up_reminder_at: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)
    # LinkedIn capture (Selenium) — extra columns for agency workflow
    agency_type: Mapped[str] = mapped_column(String(128), default="")
    problem_seen: Mapped[str] = mapped_column(Text, default="")
    last_active_display: Mapped[str] = mapped_column(String(255), default="")
    connection_sent: Mapped[str] = mapped_column(String(128), default="")
    replied_yn: Mapped[str] = mapped_column(String(8), default="N")
    solution_text: Mapped[str] = mapped_column(Text, default="")


class OutreachHistory(Base):
    __tablename__ = "outreach_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class PlatformSession(Base):
    __tablename__ = "platform_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    session_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class RawScrapeRecord(Base):
    """Append-only raw rows from Playwright scraper runs (before CRM normalization)."""

    __tablename__ = "raw_scrape_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(512), default="")
    country: Mapped[str] = mapped_column(String(128), default="")
    industry: Mapped[str] = mapped_column(String(128), default="")
    company_size: Mapped[str] = mapped_column(String(64), default="")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
