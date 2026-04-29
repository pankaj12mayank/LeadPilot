from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from backend.app.middleware.jwt import decode_access_token
from database.orm.session import get_db  # noqa: F401 — re-exported for FastAPI route ``Depends()``
from backend.services import auth_service

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Dict[str, Any]:
    """Validate JWT and load user from the database."""
    try:
        payload = decode_access_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = auth_service.get_user_by_id(sub)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive")
    return user


def require_app_roles(*allowed_roles: str):
    allowed = {str(r or "").strip().lower() for r in allowed_roles if str(r or "").strip()}

    def _inner(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        role = str(user.get("role") or "user").strip().lower()
        if role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role permission")
        return user

    return _inner


def get_current_admin(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Dict[str, Any]:
    """JWT with ``admin: true`` claim (admin console, not app users)."""
    try:
        payload = decode_access_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if not payload.get("admin"):
        raise HTTPException(status_code=403, detail="Admin token required")
    return {"admin": True, "sub": payload.get("sub")}
