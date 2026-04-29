from __future__ import annotations

from fastapi import Depends
from fastapi import APIRouter
from sqlalchemy import text

from backend.app.api.deps import get_current_user
from backend.services import debug_validation_service, runtime_settings
from database.orm.bootstrap import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    db_ok = True
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
    }


@router.get("/validation")
def health_validation(_user: dict = Depends(get_current_user)) -> dict:
    out = debug_validation_service.run_validation_checks()
    out["debug_mode"] = bool(runtime_settings.get_debug_mode())
    return out
