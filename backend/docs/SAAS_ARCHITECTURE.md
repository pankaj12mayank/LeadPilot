# Lead Intelligence SaaS — Architecture (MVP → production)

This document is the **single blueprint** for the monorepo: layout, APIs, schema, env, roadmap, and how to grow toward subscriptions.

---

## 1. Monorepo layout

```text
LeadPilot/
├── frontend/                 # React + Vite + Tailwind + React Router + Axios + Zustand + TanStack Table + Recharts
├── backend/
│   ├── app/                  # FastAPI app, routers, schemas, middleware
│   ├── modules/              # Domain packages (scraper, scorer, exporter, …)
│   └── subscriptions/      # Placeholder for Stripe / plans (future)
├── database/
│   ├── orm/                  # SQLAlchemy models + engine bootstrap
│   ├── meta_db.py            # SQLite helpers (users, legacy history tables)
│   └── migrate*.py           # CSV / migrations
├── services/                 # Application services (persistence, auth, analytics)
├── modules/                  # Legacy Python helpers (ai_enricher, lead_scorer, …)
├── exports/                  # CSV exports (gitignored contents except .gitkeep)
├── sessions/                 # Playwright storageState / session blobs (future)
├── logs/                     # Rotating file logs
├── data/                     # runtime_settings.json, CSV data (as configured)
├── prompts/                  # LLM prompt templates
├── scripts/                  # start-api.bat, etc.
├── docs/                     # This file
├── config.py                 # Central env + paths
├── requirements.txt
├── run.bat
└── .env.example
```

---

## 2. Recommended file naming

| Area | Convention | Examples |
|------|--------------|----------|
| FastAPI routes | `{domain}_routes.py` or `{domain}.py` under `backend/app/routes/` | `leads.py`, `settings_routes.py` |
| Pydantic schemas | `{entity}.py` under `backend/app/schemas/` | `lead.py`, `user.py` |
| Domain logic | `service.py` inside each `backend/modules/<domain>/` | `backend/modules/scraper/service.py` |
| SQLAlchemy | `database/orm/models.py`, `bootstrap.py` | One `Base`, explicit table names |
| React pages | `PascalCase` under `frontend/src/pages/` | `DashboardPage.tsx` |
| React layout | `layouts/` | `AppShell.tsx` |
| API client | `frontend/src/lib/api/*.ts` | One file per remote aggregate |
| Zustand | `frontend/src/store/*.ts` | `authStore.ts` |

---

## 3. Recommended API routes (current + planned)

### Implemented (MVP)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| POST | `/auth/register` | Local admin user |
| POST | `/auth/login` | JWT |
| GET | `/auth/me` | Current user |
| GET/POST/PATCH/DELETE | `/leads/*` | CRUD, bulk import, history |
| … | `/platforms/*`, `/settings/*`, `/analytics/*`, `/messages/*`, `/tools/*` | Existing product surface |

### Versioning (recommended next step)

- Mount v1 under **`/api/v1`** with thin routers that delegate to `backend/modules/*` so mobile / partners do not depend on legacy paths.
- Keep current unprefixed routes during a deprecation window.

### Future (subscription-ready)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/billing/checkout` | Stripe Checkout session |
| POST | `/api/v1/billing/webhook` | Stripe webhooks (signed) |
| GET | `/api/v1/billing/usage` | Metered limits (scrapes, exports, seats) |

---

## 4. Database schema

### 4.1 Existing SQLite (`database/api_meta.db` via `meta_db.py`)

- **users** — `id`, `email`, `password_hash`, `created_at`
- **lead_history** — audit log
- **platforms** — custom platforms
- **status_history** — CRM status transitions
- **email_history** — sent mail records

### 4.2 SQLAlchemy tables (`database/orm/models.py`, `create_all`)

| Table | Purpose |
|-------|---------|
| **outreach_history** | Unified outbound touches (email/DM/LinkedIn) with `channel`, `subject`, `body`, `status` |
| **platform_sessions** | Serialized browser/session state per `platform_slug` (Playwright) |
| **app_settings** | Key-value overrides (optional mirror of `runtime_settings.json`) |

### 4.3 Target canonical model (roadmap)

Consolidate **leads** into one SQL table (or keep pluggable `STORAGE_MODE` but add a **read model** for analytics). Add:

- **subscriptions** — `user_id`, `stripe_customer_id`, `plan`, `status`, `current_period_end`
- **usage_counters** — daily scrape count, AI tokens, exports

Until migration, **leads** remain in CSV/SQLite/Postgres via `services/lead_service.py` + `storage/`.

---

## 5. Environment variables

| Variable | Role |
|----------|------|
| `STORAGE_MODE`, `CSV_FILE_PATH`, `SQLITE_DB_PATH`, `POSTGRES_DSN` | Lead row storage |
| `API_META_DB_PATH` | Users + meta + ORM tables (same file) |
| `EXPORTS_DIR`, `SESSIONS_DIR`, `LOGS_DIR` | Paths for exports, Playwright, logs |
| `SECRET_KEY`, `JWT_*` | Auth tokens |
| `OLLAMA_URL`, `MODEL_NAME`, `USE_OLLAMA`, `FREE_API_MODE` | AI generation |
| `SMTP_*`, `SENDER_*`, `EMAIL_SIGNATURE` | Outbound email |
| `VITE_API_URL` | Frontend → API base (see `frontend/.env.example`) |

Copy **`.env.example`** → **`.env`** at repo root for Python; **`frontend/.env.example`** → **`frontend/.env`** for Vite.

---

## 6. Backend-first workflow

1. **Schema** — extend `database/meta_db.py` and/or `database/orm/models.py`; run API once to `create_all`.
2. **Service** — implement in `services/` or `backend/modules/<domain>/service.py`.
3. **Route** — add FastAPI router + Pydantic schemas; register in `backend/app/main.py`.
4. **Contract** — hit `/docs`, then add/adjust `frontend/src/lib/api/*.ts`.
5. **UI** — page in `frontend/src/pages/`, wire Zustand or local state + TanStack Table / Recharts.

---

## 7. Development roadmap

### Phase 0 — Done (this baseline)

- Monorepo folders: `exports/`, `sessions/`, `logs/`.
- `backend/modules/*` wrappers (scraper stub, cleaner, scorer, AI, CSV export, analytics, auth, settings, lead_status).
- SQLAlchemy tables for outreach / platform sessions / app settings.
- Vite frontend with Dashboard, Leads, Platforms, Analytics, Settings + sessionStorage auth.

### Phase 1 — Scraping MVP

- Implement `scraper/service.py` with Playwright (headless), store `storageState` under `sessions/`.
- BeautifulSoup fallbacks for static HTML.
- Rate limits + robots.txt checks; job queue (background worker or FastAPI `BackgroundTasks`).

### Phase 2 — Data model

- Migrate lead rows to SQLAlchemy **leads** (or materialized view) for reporting.
- Alembic migrations; retire duplicate DDL in `meta_db` gradually.

### Phase 3 — Product & billing

- `backend/subscriptions/`: Stripe customer portal, webhooks, plan entitlements.
- Middleware: `require_plan("pro")` on scrape + AI routes.
- Tenant id on `users` / `organizations` for multi-tenant SaaS.

### Phase 4 — Hardening

- Structured logging to `logs/`, rotation, request IDs.
- pytest + Playwright E2E against staging.
- CI: lint, typecheck, `npm run build`, `ruff`/`mypy` (optional).

---

## 8. Subscription-ready structure (summary)

- **Isolation** — put billing-only code in `backend/subscriptions/`; never mix with `lead_service` imports from routers directly.
- **Feature flags** — `SUBSCRIPTIONS_ENABLED` + env `STRIPE_SECRET_KEY` gated imports.
- **Entitlements** — small `entitlements.py` resolving `user_id` → `{ max_leads, scrape_per_day, seats }` from DB, cached in memory or Redis later.
- **Metering** — increment counters in `usage_counters` on scrape/export/AI calls.

---

## 9. Quick commands

- **Full stack (Windows):** `run.bat`
- **API only:** `scripts\start-api.bat`
- **Frontend only:** `cd frontend && npm run dev`
- **Playwright browsers (once):** `playwright install` (after `pip install -r requirements.txt`)

---

## 10. Frontend tech map

| Need | Package |
|------|---------|
| SPA + HMR | Vite + React 18 |
| Routing | `react-router-dom` |
| Styling | Tailwind CSS |
| HTTP | Axios (`src/lib/api/client.ts`) |
| Global auth session | Zustand + `sessionStorage` |
| Tables | `@tanstack/react-table` |
| Charts | `recharts` |

Auth token is attached as `Authorization: Bearer <jwt>` on every Axios request.
