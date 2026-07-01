from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.deps import get_current_user
from backend.app.middleware.jwt import create_access_token
from backend.app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from backend.services import auth_service, subscription_service as sub_svc

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    subscription: Optional[Dict[str, Any]] = None


def _build_user_dict(user: dict) -> UserResponse:
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user.get("name", ""),
        created_at=user["created_at"],
        is_active=bool(user.get("is_active", True)),
        role=str(user.get("role") or "user"),
        plan_id=str(user.get("plan_id") or "starter"),
        last_login_at=str(user.get("last_login_at") or ""),
    )


def _get_subscription(user_id: str) -> Optional[Dict[str, Any]]:
    sub = sub_svc.get_user_subscription(user_id)
    if sub:
        return sub_svc.handle_period_expiry(user_id)
    return None


@router.post("/register")
def register(body: UserCreate) -> AuthResponse:
    try:
        user = auth_service.create_user(body.email, body.password, role=body.role, plan_id=body.plan_id)
    except ValueError as e:
        if str(e) == "email_taken":
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(status_code=400, detail="Registration failed")

    # Auto-assign free plan subscription
    free_plans = sub_svc.list_plans(include_inactive=False)
    free_plan = next((p for p in free_plans if p.get("is_free")), None)
    if free_plan:
        sub_svc.create_free_subscription(user["id"], free_plan["id"])
        sub_svc.send_welcome_email(user["id"])

    token = create_access_token(user["id"], {"role": user.get("role", "user"), "plan_id": user.get("plan_id", "starter")})
    sub = _get_subscription(user["id"])
    return AuthResponse(
        access_token=token,
        user=_build_user_dict(user),
        subscription=sub,
    )


@router.post("/login")
def login(body: UserLogin) -> AuthResponse:
    user = auth_service.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    # Check if user has any subscription at all
    sub = _get_subscription(user["id"])
    if not sub:
        # Auto-assign free plan
        free_plans = sub_svc.list_plans(include_inactive=False)
        free_plan = next((p for p in free_plans if p.get("is_free")), None)
        if free_plan:
            sub_svc.create_free_subscription(user["id"], free_plan["id"])
            sub = _get_subscription(user["id"])

    token = create_access_token(user["id"], {"role": user.get("role", "user"), "plan_id": user.get("plan_id", "starter")})
    return AuthResponse(
        access_token=token,
        user=_build_user_dict(user),
        subscription=sub,
    )


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> AuthResponse:
    sub = _get_subscription(user["id"])
    return AuthResponse(
        access_token="",
        user=_build_user_dict(user),
        subscription=sub,
    )
