import os
from pathlib import Path

from dotenv import load_dotenv

# Always load ``LeadPilot/.env`` (next to this file), not only cwd — fixes admin env when API is started from another folder.
_REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(_REPO_ROOT / ".env")
load_dotenv()  # optional: cwd .env overrides for local experiments

DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip() or "INFO"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").strip() or "*"

CSV_FILE_PATH = os.getenv("CSV_FILE_PATH", "data/leads.csv")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "database/leads.db")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")
STORAGE_MODE = os.getenv("STORAGE_MODE", "csv").lower().strip()

PROMPTS_DIR = os.getenv("PROMPTS_DIR", "prompts")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")

# Ollama message generator (Llama3 / Mistral / DeepSeek tags — match your ``ollama list``)
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
OLLAMA_MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))
OLLAMA_MODEL_LLAMA3 = os.getenv("OLLAMA_MODEL_LLAMA3", "llama3").strip() or "llama3"
OLLAMA_MODEL_MISTRAL = os.getenv("OLLAMA_MODEL_MISTRAL", "mistral").strip() or "mistral"
OLLAMA_MODEL_DEEPSEEK = os.getenv("OLLAMA_MODEL_DEEPSEEK", "deepseek-r1").strip() or "deepseek-r1"

USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() in ("1", "true", "yes")
FREE_API_MODE = os.getenv("FREE_API_MODE", "false").lower() in ("1", "true", "yes")

API_KEYS = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]

# JWT (API). Change SECRET_KEY in production.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # default 7 days

API_META_DB_PATH = os.getenv("API_META_DB_PATH", "database/api_meta.db")

# Admin console (separate from app users). Set both to enable /admin login.
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()

# Monorepo paths (CSV exports, Playwright session state, app logs)
EXPORTS_DIR = os.getenv("EXPORTS_DIR", "exports").strip() or "exports"
SESSIONS_DIR = os.getenv("SESSIONS_DIR", "sessions").strip() or "sessions"
LOGS_DIR = os.getenv("LOGS_DIR", "logs").strip() or "logs"

# Uploaded logo / favicon (served at ``/branding/*``)
BRANDING_UPLOAD_DIR = os.getenv("BRANDING_UPLOAD_DIR", str(_REPO_ROOT / "storage" / "branding")).strip() or str(
    _REPO_ROOT / "storage" / "branding"
)


def ensure_data_dirs() -> None:
    for d in (EXPORTS_DIR, SESSIONS_DIR, LOGS_DIR, BRANDING_UPLOAD_DIR):
        os.makedirs(d, exist_ok=True)
    for p in (SQLITE_DB_PATH, API_META_DB_PATH, SAFE_CAPTURE_DB_PATH, SAFE_CAPTURE_CSV_PATH):
        parent = os.path.dirname(os.path.abspath(p))
        if parent:
            os.makedirs(parent, exist_ok=True)
    os.makedirs(SAFE_CAPTURE_PROFILE_DIR, exist_ok=True)


# --- Scraper (Playwright): safe delays & per-run lead caps ---
SCRAPER_DELAY_MIN_SECONDS = float(os.getenv("SCRAPER_DELAY_MIN_SECONDS", "3"))
SCRAPER_DELAY_MAX_SECONDS = float(os.getenv("SCRAPER_DELAY_MAX_SECONDS", "5"))
SCRAPER_MAX_LEADS_DEFAULT = int(os.getenv("SCRAPER_MAX_LEADS_DEFAULT", "20"))
SCRAPER_MAX_LEADS_HARD_CAP = int(os.getenv("SCRAPER_MAX_LEADS_HARD_CAP", "50"))
SCRAPER_MANUAL_LOGIN_DEFAULT_SECONDS = int(os.getenv("SCRAPER_MANUAL_LOGIN_DEFAULT_SECONDS", "180"))
# When ``profile_contact_enrich`` is on, max profiles to open for public mailto/tel (0 disables enrich).
SCRAPER_PROFILE_ENRICH_CAP = int(os.getenv("SCRAPER_PROFILE_ENRICH_CAP", "8"))

# --- Lead scoring (industry alignment bonus) ---
SCORING_BENCHMARK_INDUSTRY = os.getenv("SCORING_BENCHMARK_INDUSTRY", "").strip()

# --- Safe manual capture (Playwright + sqlite3; one lead at a time) ---
_REPO_ROOT_STR = str(_REPO_ROOT)
SAFE_CAPTURE_DB_PATH = os.getenv(
    "SAFE_CAPTURE_DB_PATH",
    str(_REPO_ROOT / "database" / "safe_leads.db"),
).strip()
SAFE_CAPTURE_PROFILE_DIR = os.getenv(
    "SAFE_CAPTURE_PROFILE_DIR",
    str(_REPO_ROOT / "sessions" / "playwright_user_data" / "safe_capture"),
).strip()
SAFE_CAPTURE_CSV_PATH = os.getenv(
    "SAFE_CAPTURE_CSV_PATH",
    str(_REPO_ROOT / "exports" / "safe_leads.csv"),
).strip()
SAFE_CAPTURE_LOCK_PATH = os.getenv(
    "SAFE_CAPTURE_LOCK_PATH",
    str(_REPO_ROOT / "sessions" / "safe_capture.lock"),
).strip()


# SMTP (optional — email_service sends when host is set)
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
SENDER_NAME = os.getenv("SENDER_NAME", "Lead Engine")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip() or SMTP_EMAIL
EMAIL_SIGNATURE = os.getenv("EMAIL_SIGNATURE", "").replace("\\n", "\n")