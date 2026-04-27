# Lead Intelligence (LeadPilot)

Monorepo: **FastAPI** backend + **React (Vite)** SPA. CRM leads live in **SQLite** via SQLAlchemy (`API_META_DB_PATH`). Optional **Playwright** scrapers persist sessions under `sessions/` and write `exports/` + raw tables.

---

## Final commands (cheat sheet)

| Action | Command |
|--------|---------|
| **Backend (dev, reload)** | From repo root: `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| **Frontend (dev)** | `cd frontend && npm run dev` → [http://localhost:5173](http://localhost:5173) |
| **One-command local (API + Vite)** | **Windows:** double-click **`run.bat`** from the repo root (installs deps, then runs **API + Vite in one window** — leave it open; **Ctrl+C** stops both). **Manual:** `.\.venv\Scripts\python.exe scripts\dev_server.py` from repo root, or `scripts\start-api.bat` + `scripts\start-frontend.bat` in two terminals |
| **Production build (SPA only)** | `cd frontend && npm run build` (output: `frontend/dist/`) |
| **Docker Compose (API + nginx UI)** | `docker compose up --build` → API [http://127.0.0.1:8000](http://127.0.0.1:8000), UI [http://127.0.0.1:8080](http://127.0.0.1:8080) |
| **Initialize SQLite / dirs** | `python scripts/init_database.py` |
| **Seed demo user + leads** | `python scripts/seed_demo_data.py` |
| **API tests** | `pip install -r requirements.txt` then `pytest` |
| **Frontend tests** | `cd frontend && npm run test` |
| **All tests** | API: `pytest` · Web: `cd frontend && npm run test` |
| **Selenium LinkedIn + full pipeline (scrape → enrich → score)** | **UI:** Lead search page → **LinkedIn desktop pipeline (Selenium)** — runs `python -m backend.leadpilot` on the API host. **CLI (repo root):** `python leadpilot_single.py` or `python -m backend.leadpilot` or `python -m backend.leadpilot.lead_scraper` — see **Selenium LinkedIn pipeline** below. Push uses **`LNN_BASE_URL`** (UI sets it to this API automatically). |

API docs (when backend is up): **http://127.0.0.1:8000/docs** (OpenAPI paths include the **`/api`** prefix by default)

---

## Repository layout (deployment-oriented)

```text
LeadPilot/
├── app/                      # Thin package: `uvicorn app.main:app` re-exports `backend.app.main`
├── leadpilot_single.py       # Shim → `backend.leadpilot.main` (same as `python -m backend.leadpilot`)
├── scraper.env.example       # Template for `scraper.env` (optional; `run.bat` may create `scraper.env` once)
├── scraper.env               # Local overrides (optional); loaded after `.env` by Selenium tools
├── backend/                  # FastAPI + Selenium LinkedIn pipeline package
│   ├── leadpilot/            # Chrome/Selenium: `scraper_core`, `lead_scraper`, `preflight`, pipeline (`python -m backend.leadpilot`)
│   ├── app/main.py           # FastAPI entry + lifespan
│   ├── services/             # Auth, ORM leads, analytics, messaging, …
│   ├── connectors/         # Safe-capture parsers + platform ids
│   ├── safe_capture/         # Manual capture normalize / score / AI helpers
│   ├── storage/             # CSV / SQLite / Postgres storage adapters
│   ├── settings/            # lead_schema (shared constants)
│   ├── utils/               # logging, locks, platform_detect
│   ├── prompts/             # LLM text templates (PROMPTS_DIR default)
│   └── docs/                # Architecture notes (optional)
├── config.py                 # Central env (python-dotenv); load from repo root
├── database/                 # ORM bootstrap, meta_db, safe_capture_store
├── exports/                  # CSV outputs (Docker volume)
├── sessions/                 # Playwright profiles (volume)
├── logs/
├── data/                     # Default CSV path for STORAGE_MODE=csv (optional)
├── scripts/
│   ├── init_database.py
│   ├── seed_demo_data.py
│   ├── start-api.bat         # API only (.venv + uvicorn)
│   └── start-frontend.bat    # Vite dev server only
├── tests/                    # Pytest
├── frontend/                 # Vite + React (single package.json here)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt          # All Python deps (app + pytest + ruff)
├── pytest.ini
├── run.bat                   # Windows: venv, pip, DB init, import check, then API + Vite (see `scripts\dev_server.py`)
└── .env.example
```

### Selenium LinkedIn pipeline (one project, repo root)

Run **from the repository root** (same folder as `config.py`). `scraper_core` loads **`.env`** then **`scraper.env`** (later wins on duplicate keys).

| Goal | Command |
|------|--------|
| **Full run** (LinkedIn → Apollo/Skrapp → score → `.xlsx`) | `python leadpilot_single.py` or `python -m backend.leadpilot` |
| **Quick test** (caps leads when `LEADPILOT_TEST=1` / `--test`) | `python leadpilot_single.py --test -n 5` |
| **Excel-only legacy** (no enrichment step) | `python -m backend.leadpilot.lead_scraper` |
| **Health checks only** | `python -m backend.leadpilot.lead_scraper --verify-only` |

Pipeline code lives under **`backend/leadpilot/`** (`scraper.py` wraps `collect_linkedin_leads` in `lead_scraper.py`, plus `enrichment.py`, `scoring.py`, `export.py`, `scraper_core.py`, `preflight.py`). Set **`APOLLO_API_KEY`**, **`SKRAPP_API_KEY`** for enrichment; **`LNN_BASE_URL`** to push rows into this app’s API.

---

## Environment variables

1. **Backend:** copy **`.env.example`** → **`.env`** in the **repository root** (same folder as `config.py`). `python-dotenv` loads this on import.
2. **Frontend:** optional **`frontend/.env`**.  
   - **Development:** leave **`VITE_API_BASE_URL`** unset → Axios uses **`/api`** and Vite proxies **`/api/*` → `http://127.0.0.1:8000`** (same path; see `frontend/vite.config.ts`).  
   - **Production build:** set **`VITE_API_BASE_URL`** to the browser-reachable API root including the prefix, e.g. **`https://api.example.com/api`** (legacy: `VITE_API_URL`).

Important keys:

| Variable | Purpose |
|----------|---------|
| `API_META_DB_PATH` | SQLite file for users, leads (ORM), settings, raw scrape rows |
| `SECRET_KEY` | JWT signing — **change in production** |
| `CORS_ORIGINS` | Comma-separated allowed origins (use real UI origin in prod; avoid `*` if you need credentials) |
| `FRONTEND_URL` | Vite origin (e.g. `http://localhost:5173`); appended to `CORS_ORIGINS` when that list is explicit |
| `API_ROOT_PATH` | JSON API prefix (default **`/api`**). **`GET /health`** and **`/branding/*`** stay at the server root |
| `EXPORTS_DIR`, `SESSIONS_DIR`, `LOGS_DIR` | Writable runtime directories |
| `VITE_API_BASE_URL` | Axios base URL for the SPA (build-time; include `/api` to match `API_ROOT_PATH`) |

---

## Frontend ↔ backend (Axios)

- **`frontend/src/lib/api/client.ts`** creates a shared Axios instance with `Authorization: Bearer <token>` from Zustand.
- **Dev:** default base URL is **`/api`**; Vite proxies **`/api/*`** to **`http://127.0.0.1:8000`** with the same path (no strip).
- **Prod:** set **`VITE_API_BASE_URL`** at `npm run build` time (e.g. `http://127.0.0.1:8000/api`) and align **`CORS_ORIGINS`** / **`FRONTEND_URL`** on the API.

---

## SQLite initialization

On every API startup (`lifespan` in `backend/app/main.py`):

1. `setup_logging()` — console + `logs/api.log` (rotating).
2. `config.ensure_data_dirs()` — exports, sessions, logs, and parent dirs for DB files.
3. `init_meta_schema()` — legacy/meta tables in `API_META_DB_PATH`.
4. `init_sa_tables()` — SQLAlchemy `Base.metadata.create_all` + light migrations.
5. `lead_service.init_storage()` — CSV/SQLite/Postgres storage per `STORAGE_MODE`.

You can run the same steps without starting the server:

```bash
python scripts/init_database.py
```

---

## Local deployment (without Docker)

**Prerequisites:** Python 3.11+, Node 20+, `pip`, `npm`.

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
copy .env.example .env                 # Windows: copy; Unix: cp
python scripts/init_database.py
python scripts/seed_demo_data.py       # optional demo login (see script env vars)
```

**Option A — Windows (recommended):** double-click **`run.bat`** from the repo root (installs/updates venv and deps, initializes DB, verifies `app` + `backend.leadpilot` imports, then starts **API + Vite** in one window).

**Option B — manual two terminals:** `scripts\start-api.bat` then `scripts\start-frontend.bat` (or `uvicorn` / `npm run dev` yourself from repo root / `frontend\`).

**Option C — Unix / macOS:** same as B with `uvicorn` + `npm run dev` in two shells (no root `run.sh`; keep it simple).

Sign in with seeded **`demo@leadpilot.local`** / **`demo-password-change-me`** (unless overridden by `SEED_DEMO_EMAIL` / `SEED_DEMO_PASSWORD`).

---

## Docker

```bash
docker compose up --build
```

- **API** listens on **8000**; volumes persist `database/`, `exports/`, `logs/`, `sessions/`.
- **Web** is nginx on host **8080**; the SPA is built with **`VITE_API_BASE_URL`** defaulting to **`http://127.0.0.1:8000/api`**.  
  Adjust in compose: `VITE_API_BASE_URL`, `API_ROOT_PATH`, `FRONTEND_URL`, `CORS_ORIGINS`, `SECRET_KEY`.

Playwright scrapers need a **saved session** on the host volume (`sessions/`); use **`POST /api/scraper/sessions/{platform}/manual-login`** from a machine that can open a browser, or document X11 for headed login in Linux containers.

---

## Error logging

- **Application:** `backend/app/logging_config.py` — root logger to stdout and **`logs/api.log`** (2 MB × 3 files). Level from **`LOG_LEVEL`**.
- **HTTP:** `backend/app/middleware/error_handlers.py` — validation errors **422**; unhandled exceptions **500** with `logger.exception`; **4xx/5xx** Starlette HTTP exceptions logged at **warning/error** with method and path.

---

## Testing

**API (pytest):** from repo root with `PYTHONPATH` implicit via `pytest.ini`:

```bash
pip install -r requirements.txt
pytest
```

**Frontend (Vitest):**

```bash
cd frontend && npm install && npm run test
```

If `npm ci` fails in Docker, refresh `frontend/package-lock.json` locally (`npm install` in `frontend/`) after dependency changes.

---

## Production build scripts

```bash
cd frontend
npm ci
npm run build
```

Serve `frontend/dist/` with any static host; align **`VITE_API_BASE_URL`** with your gateway path (usually ends in **`/api`**) and **`API_ROOT_PATH`** on the API.

---

## API quick reference

Default **`API_ROOT_PATH=/api`** (override with env). Public branding: **`GET /api/public/branding`**.

- **Auth:** `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- **Leads:** `GET/POST /api/leads`, exports under `/api/exports/`
- **Scraper:** `GET /api/scraper/status`, `POST /api/scraper/run`, `GET /api/scraper/jobs/{id}`
- **Health:** `GET /health` (no `/api` prefix)

Architecture notes: **`backend/docs/SAAS_ARCHITECTURE.md`**.
