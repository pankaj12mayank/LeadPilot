from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from backend.app.logging_config import setup_logging
from backend.app.middleware.error_handlers import register_exception_handlers
from backend.app.routes import (
    admin,
    ai_messages,
    analytics,
    auth,
    companies,
    exports,
    health,
    leads,
    messages,
    platforms,
    public,
    scraper,
    settings_routes,
    selenium_leadpilot,
    subscriptions,
    tools,
)
from database.meta_db import init_meta_schema
from database.orm.bootstrap import init_sa_tables
from backend.services import lead_service, runtime_settings, settings_service, task_queue_service, subscription_service

_startup_log = logging.getLogger("leadpilot.startup")


def _log_config_update(event: dict) -> None:
    changed = [str(x) for x in (event.get("changed_fields") or [])]
    _startup_log.info(
        "Received %s event at %s for fields=%s",
        event.get("event"),
        event.get("timestamp"),
        changed,
    )
    requires_rescore = any(
        f.startswith("admin_config.scoring_weights")
        or f.startswith("admin_config.scoring_control")
        or f.startswith("admin_config.signals_config")
        for f in changed
    )
    if not requires_rescore:
        return
    cfg = runtime_settings.get_admin_config()
    pri = str((cfg.get("task_priority") or {}).get("scoring") or "high").strip().lower()
    if pri not in {"high", "medium", "low"}:
        pri = "high"
    queued = task_queue_service.enqueue(
        {
            "task_type": "scoring",
            "priority": pri,
            "requires_login": False,
            "payload": {"batch": "config_updated_scoring", "source_event": "config_updated"},
        }
    )
    _startup_log.info("Queued scoring refresh after config update: %s", queued)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    _startup_log.info("LeadPilot API — startup beginning.")
    _startup_log.info("python-dotenv: loaded .env from repository root (see config.py).")
    config.ensure_data_dirs()
    _startup_log.info("Runtime directories ready (exports, sessions, logs, DB parents, branding).")
    init_meta_schema()
    _startup_log.info("Meta SQLite schema OK (%s).", getattr(config, "API_META_DB_PATH", ""))
    init_sa_tables()
    _startup_log.info("SQLAlchemy tables OK (ORM / leads schema).")
    lead_service.init_storage()
    _startup_log.info("Lead storage initialized (STORAGE_MODE=%s).", getattr(config, "STORAGE_MODE", ""))
    cfg = runtime_settings.get_admin_config()
    _startup_log.info(
        "Admin config loaded (session expiry=%s day(s), retry_count=%s).",
        cfg.get("session_policy", {}).get("expiry_days"),
        cfg.get("retry_policy", {}).get("retry_count"),
    )
    settings_service.subscribe_config_updates(_log_config_update)
    subscription_service.seed_default_plans()
    subscription_service.seed_default_email_templates()
    _startup_log.info("LeadPilot API — ready to accept requests.")
    yield
    settings_service.unsubscribe_config_updates(_log_config_update)
    _startup_log.info("LeadPilot API — shutdown.")


app = FastAPI(
    title="LeadPilot API",
    version="1.0.0",
    lifespan=lifespan,
    debug=bool(getattr(config, "DEBUG", False)),
)

register_exception_handlers(app)

# Wildcard origins cannot be combined with allow_credentials=True (browser + Starlette rules).
_cors_origins = [o.strip().rstrip("/") for o in config.CORS_ORIGINS.split(",") if o.strip()]
if not _cors_origins:
    _cors_origins = ["*"]
if config.FRONTEND_URL and _cors_origins != ["*"]:
    fu = config.FRONTEND_URL.strip().rstrip("/")
    if fu and fu not in _cors_origins:
        _cors_origins.append(fu)
_allow_credentials = all(o != "*" for o in _cors_origins)
if not _allow_credentials:
    logging.getLogger("leadpilot.startup").info(
        "CORS: wildcard origin(s) detected — allow_credentials=False for browser compatibility."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

_api_root = config.API_ROOT_PATH or ""

app.include_router(health.router)
app.include_router(public.router, prefix=_api_root)
app.include_router(admin.router, prefix=_api_root)
app.include_router(auth.router, prefix=_api_root)
app.include_router(companies.router, prefix=_api_root)
app.include_router(leads.router, prefix=_api_root)
app.include_router(messages.router, prefix=_api_root)
app.include_router(ai_messages.router, prefix=_api_root)
app.include_router(platforms.router, prefix=_api_root)
app.include_router(settings_routes.router, prefix=_api_root)
app.include_router(analytics.router, prefix=_api_root)
app.include_router(exports.router, prefix=_api_root)
app.include_router(scraper.router, prefix=_api_root)
app.include_router(selenium_leadpilot.router, prefix=_api_root)
app.include_router(tools.router, prefix=_api_root)
app.include_router(subscriptions.router, prefix=_api_root)

_startup_log.info(
    "HTTP API routes mounted under %r (GET /health unchanged; static /branding unchanged).",
    (_api_root + "/*") if _api_root else "/* (no API_ROOT_PATH prefix)",
)

_branding_dir = Path(config.BRANDING_UPLOAD_DIR)
_branding_dir.mkdir(parents=True, exist_ok=True)
app.mount("/branding", StaticFiles(directory=str(_branding_dir)), name="branding")
