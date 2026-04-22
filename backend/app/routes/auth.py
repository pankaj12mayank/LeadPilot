from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.deps import get_current_user
from backend.app.middleware.jwt import create_access_token
from backend.app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from backend.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(body: UserCreate) -> TokenResponse:
    try:
        user = auth_service.create_user(body.email, body.password)
    except ValueError as e:
        if str(e) == "email_taken":
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(status_code=400, detail="Registration failed")
    token = create_access_token(user["id"])
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            created_at=user["created_at"],
            is_active=bool(user.get("is_active", True)),
            last_login_at=str(user.get("last_login_at") or ""),
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin) -> TokenResponse:
    user = auth_service.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(user["id"])
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            created_at=user["created_at"],
            is_active=bool(user.get("is_active", True)),
            last_login_at=str(user.get("last_login_at") or ""),
        ),
    )


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=user["id"],
        email=user["email"],
        created_at=user["created_at"],
        is_active=bool(user.get("is_active", True)),
        last_login_at=str(user.get("last_login_at") or ""),
    )
