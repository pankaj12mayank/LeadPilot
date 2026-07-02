# LeadPilot

Production-ready monorepo for lead intelligence and sales CRM:

- **FastAPI** backend (`backend/app/main.py`)
- **React + Vite** frontend (`frontend/`)
- **SQLite** metadata + ORM tables (PostgreSQL optional)

---

## Quick Start

```bash
python scripts/run_system.py
```

This single command will:
1. Create `.venv` if missing
2. Install Python dependencies
3. Install frontend dependencies (`npm ci` / `npm install`)
4. Install Playwright browser binaries
5. Initialize DB and runtime directories
6. Start backend (`127.0.0.1:8000`) and frontend (`localhost:5173`)

Press `Ctrl+C` once to stop both services.

---

## Manual Setup

### 1. Install Dependencies

```bash
# Backend (Python)
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt

# Playwright browser binaries (required for LinkedIn scraping)
.venv\Scripts\python -m playwright install chromium

# Frontend (Node.js)
cd frontend
npm install
cd ..
```

### 2. Initialize Database

```bash
.venv\Scripts\python scripts/init_database.py
```

### 3. Run Backend

Run from **repo root**:
```bash
.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or from **`backend/` folder**:
```bash
..\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or using the convenience script from **repo root**:
```bash
.venv\Scripts\python backend\run.py
```

### 4. Run Frontend (separate terminal)

```bash
cd frontend
npm run dev
```

The Vite dev server (port 5173) proxies `/api` requests to the backend on port 8000.

---

## URLs

| Service | URL | Notes |
|---------|-----|-------|
| Frontend (dev) | http://localhost:5173 | Vite dev server, proxies /api → backend |
| Frontend (prod) | http://localhost:4173 | `npm run preview` after build |
| Backend API | http://127.0.0.1:8000 | FastAPI + Uvicorn |
| API Docs (Swagger) | http://127.0.0.1:8000/docs | Interactive API explorer |
| API Docs (ReDoc) | http://127.0.0.1:8000/redoc | Alternative docs UI |
| Health Check | http://127.0.0.1:8000/health | Quick uptime check |

Default API root path for app routes is `/api` (configurable via `API_ROOT_PATH`).

---

## Configuration

Main config source:

- Root `.env` (copy from `.env.example` if missing)

Frontend env:

- `frontend/.env` (copied from `frontend/.env.example` automatically when missing)

Most important variables:

- `SECRET_KEY` — JWT secret (**must change for production**)
- `CORS_ORIGINS` — allowed frontend origins
- `FRONTEND_URL` — frontend URL for CORS
- `STORAGE_MODE` — `csv`, `sqlite` (default), or `postgres`

---

## User Roles

| Role | Capabilities |
|------|-------------|
| **User** | Lead CRM (search, leads, outreach), analytics, profile, transactions, upgrade/checkout |
| **Buyer** | Buyer dashboard, lead pack marketplace, purchases |
| **Admin** | Full system control: user management, plans, scoring, sources, branding, payment gateway, email config, transactions |

## Frontend Routes

### Protected App Pages (`/` — inside AppShell sidebar)

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard` | DashboardPage | KPIs, stats cards, plan usage bar, system overview |
| `/buyer-dashboard` | BuyerDashboardPage | Marketplace lead pack purchases |
| `/search-leads` | SearchLeadsPage | Explorer — search companies and discover leads |
| `/leads` | LeadsPage | Full lead CRM table with filters, bulk actions, export |
| `/outreach-queue` | OutreachQueuePage | AI message generation queue |
| `/analytics` | AnalyticsPage | Charts: funnel, timeline, platform/status breakdown |
| `/settings` | SettingsPage | User preferences |
| `/user/transactions` | UserTransactionsPage | Payment history with filters |
| `/user/upgrade` | UserUpgradePage | Plan selection cards |
| `/user/checkout/:planId` | UserCheckoutPage | Payment checkout (Stripe/Razorpay) |
| `/user/profile` | UserProfilePage | Name, email, password management |

### Admin Pages (`/admin/*`)

| Route | Description |
|-------|-------------|
| `/admin/overview` | Workspace stats, registered users, total leads |
| `/admin/users` | User CRUD, set passwords, manage roles |
| `/admin/branding` | Logo, favicon, product name, copyright |
| `/admin/lead-packs` | Lead pack marketplace management |
| `/admin/scoring` | Scoring weights, signals config |
| `/admin/plans` | Subscription plan CRUD with pricing |
| `/admin/sources` | Source toggles and config |
| `/admin/job-logs` | Scraper job run history |
| `/admin/profile` | Admin profile management |
| `/admin/newsletter` | Landing page subscribers |
| `/admin/inbox` | Contact form messages |
| `/admin/payment-gateway` | Stripe/Razorpay API key config |
| `/admin/email-config` | SMTP settings |
| `/admin/email-templates` | Transactional email template management |
| `/admin/transactions` | All transactions with filters |

### Landing Pages (public, `/` — no sidebar)

| Route | Description |
|-------|-------------|
| `/` | Home page with hero, features, pricing |
| `/features` / `/features/:slug` | Features overview + detail |
| `/pricing` | Public pricing page |
| `/subscribe/:planId` | Public checkout (legacy — use `/user/checkout/:planId` for logged-in users) |
| `/payment/success` / `/payment/failed` | Payment result pages |
| `/blog` / `/blog/:slug` | Blog listing + article |
| `/contact` / `/about` | Contact form + about us |
| `/terms` / `/privacy` | Legal pages |
| `/404` | Not found |

## Usage Flow

1. Start system: `python scripts/run_system.py`
2. Open frontend at http://localhost:5173 and login/register
3. Use Admin panel for source toggles, AI/scoring controls
4. Use Explorer / Leads / Outreach / Buyer flows as per role
5. Upgrade from sidebar or dashboard → plan selection → checkout → payment

---

## Testing

```bash
# Backend
.venv\Scripts\python -m pytest

# Frontend
cd frontend && npm run test
```

---

## Production Notes

- Replace default `SECRET_KEY` and restrict `CORS_ORIGINS`
- Build frontend: `cd frontend && npm run build`
- Deploy API + static frontend behind a reverse proxy
- Keep SQLite file paths on persistent storage
