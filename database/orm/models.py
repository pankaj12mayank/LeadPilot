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
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user", index=True)
    plan_id: Mapped[str] = mapped_column(String(32), nullable=False, default="starter", index=True)
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
    signal_hiring: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    signal_scaling: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    signal_content_gap: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    signal_ads_gap: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    priority: Mapped[str] = mapped_column(String(16), default="Cold", index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, default="", index=True)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(Text, default="", index=True)
    website: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(Text, default="", index=True)
    signals: Mapped[str] = mapped_column(Text, default="")
    ai_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    first_seen: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    last_updated: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class CompanyEnrichment(Base):
    __tablename__ = "company_enrichment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    source_url: Mapped[str] = mapped_column(Text, default="")
    has_blog: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_careers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_text: Mapped[str] = mapped_column(Text, default="")
    signal_hiring: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    signal_scaling: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    signal_content_gap: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    signal_ads_gap: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    priority: Mapped[str] = mapped_column(String(16), default="Cold", index=True)
    fetch_ok: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    fetch_error: Mapped[str] = mapped_column(Text, default="")
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    ai_problems: Mapped[str] = mapped_column(Text, default="")
    ai_opportunity: Mapped[str] = mapped_column(Text, default="")
    ai_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    ai_provider: Mapped[str] = mapped_column(String(32), default="", index=True)
    ai_cache_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    ai_updated_at: Mapped[str] = mapped_column(String(64), default="", index=True)
    last_checked: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


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


class LandingConfigState(Base):
    __tablename__ = "landing_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class AdminConfigState(Base):
    __tablename__ = "admin_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


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


class TaskQueueItem(Base):
    __tablename__ = "task_queue_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", index=True)
    requires_login: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    queue_state: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", index=True)  # queued|waiting|failed
    waiting_reason: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class LeadPack(Base):
    __tablename__ = "lead_packs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    lead_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    price_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    created_by: Mapped[str] = mapped_column(String(36), default="", index=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class LeadPackPurchase(Base):
    __tablename__ = "lead_pack_purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pack_id: Mapped[int] = mapped_column(Integer, ForeignKey("lead_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    buyer_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed", index=True)
    purchased_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    monthly_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="usd")
    features: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    highlighted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_free: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    lead_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    channel_access: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    stripe_price_id: Mapped[str] = mapped_column(String(128), default="")
    razorpay_plan_id: Mapped[str] = mapped_column(String(128), default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_payment", index=True)
    start_date: Mapped[str] = mapped_column(String(64), default="")
    end_date: Mapped[str] = mapped_column(String(64), default="")
    trial_end: Mapped[str] = mapped_column(String(64), default="")
    stripe_sub_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    razorpay_sub_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    gateway: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    auto_renew: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subscription_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="usd")
    gateway: Mapped[str] = mapped_column(String(32), nullable=False, default="stripe")
    gateway_txn_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    gateway_sub_id: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    payment_method: Mapped[str] = mapped_column(String(64), default="")
    failure_reason: Mapped[str] = mapped_column(Text, default="")
    invoice_url: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class PaymentGatewayConfig(Base):
    __tablename__ = "payment_gateway_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    gateway: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    publishable_key: Mapped[str] = mapped_column(Text, default="")
    secret_key: Mapped[str] = mapped_column(Text, default="")
    webhook_secret: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class EmailConfig(Base):
    __tablename__ = "email_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    smtp_host: Mapped[str] = mapped_column(String(255), default="")
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=587)
    smtp_user: Mapped[str] = mapped_column(String(255), default="")
    smtp_pass: Mapped[str] = mapped_column(Text, default="")
    from_email: Mapped[str] = mapped_column(String(320), default="")
    from_name: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    variables: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class UserUsage(Base):
    __tablename__ = "user_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subscription_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    leads_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    period_start: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    period_end: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    subscribed_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    source: Mapped[str] = mapped_column(String(64), default="")


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(64), default="")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unread", index=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
