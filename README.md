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

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API Docs | http://127.0.0.1:8000/docs |
| Health   | http://127.0.0.1:8000/health |

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

## Usage Flow

1. Start system: `python scripts/run_system.py`
2. Open frontend and login/register
3. Use Admin panel for source toggles, AI/scoring controls
4. Use Explorer / Leads / Outreach / Buyer flows as per role

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
