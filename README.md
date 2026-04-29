# LeadPilot

Production-ready monorepo for LeadPilot:

- FastAPI backend (`app.main:app`)
- React + Vite frontend (`frontend/`)
- SQLite metadata + ORM tables

This README is optimized for one-command startup with minimal confusion.

---

## One Command (recommended)

From repo root:

```bash
python scripts/run_system.py
```

This single command will:

1. Create `.venv` if missing
2. Install Python dependencies from `requirements.txt`
3. Install frontend dependencies (`npm ci` when lockfile exists)
4. Initialize DB and runtime directories
5. Start backend (`127.0.0.1:8000`) and frontend (`localhost:5173`)

Press `Ctrl+C` once to stop both services.

---

## Setup Only / Run Only

If you want explicit phases:

```bash
python scripts/run_system.py --setup-only
python scripts/run_system.py --run-only
```

---

## Manual Setup (fallback)

Use only if needed:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
cd frontend && npm ci && cd ..
.venv\Scripts\python scripts/init_database.py
```

Then run:

```bash
python scripts/run_system.py --run-only
```

---

## URLs

- Frontend: [http://localhost:5173](http://localhost:5173)
- API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

Default API root path for app routes is `/api` (configurable via `API_ROOT_PATH`).

---

## Configuration Explained

Main config source:

- Root `.env` (copy from `.env.example` if missing)

Frontend env:

- `frontend/.env` (copied from `frontend/.env.example` automatically when missing)

Most important variables:

- `API_META_DB_PATH`: SQLite metadata DB path
- `API_ROOT_PATH`: API prefix (default `/api`)
- `SECRET_KEY`: JWT secret (**must change for production**)
- `CORS_ORIGINS`: allowed frontend origins
- `FRONTEND_URL`: frontend URL for CORS expansion
- `LOGS_DIR`, `EXPORTS_DIR`, `SESSIONS_DIR`: runtime directories
- `VITE_API_BASE_URL`: frontend API base URL for production builds

Runtime admin controls (including debug mode) are stored via settings/admin config and loaded dynamically.

---

## Usage Flow

1. Start system:
   - `python scripts/run_system.py`
2. Open frontend and login/register.
3. Use Admin panel for:
   - source toggles
   - AI/scoring controls
   - queue/safety controls
4. Use Explorer / Leads / Outreach / Buyer flows as per role.

---

## Troubleshooting

- **`python` not found**
  - Install Python 3.11+ and ensure `python` is in PATH.

- **`npm` not found**
  - Install Node.js LTS (includes npm), restart terminal.

- **Frontend fails to start (`npm ci` issues)**
  - Run `cd frontend && npm install` once, then retry.

- **DB init error**
  - Run `python scripts/run_system.py --setup-only` and inspect output.
  - Confirm write access to `database/`, `logs/`, `exports/`, `sessions/`.

- **Port already in use (8000 / 5173)**
  - Stop old process, then rerun command.

- **Auth/CORS issues**
  - Verify `.env` values for `API_ROOT_PATH`, `CORS_ORIGINS`, `FRONTEND_URL`, `SECRET_KEY`.

- **Need diagnostic checks**
  - Use `GET /validation` (authenticated) and `GET /health`.

---

## Testing

Backend:

```bash
.venv\Scripts\python -m pytest
```

Frontend:

```bash
cd frontend && npm run test
```

---

## Production Notes

- Replace default `SECRET_KEY` and restrict `CORS_ORIGINS`.
- Build frontend with proper API URL:
  - `cd frontend && npm run build`
- Deploy API + static frontend behind a reverse proxy.
- Keep SQLite file paths on persistent storage.
