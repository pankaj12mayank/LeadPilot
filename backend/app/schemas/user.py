from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="user")
    plan_id: str = Field(default="starter")


class UserLogin(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str = ""
    created_at: str
    is_active: bool = True
    role: str = "user"
    plan_id: str = "starter"
    last_login_at: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None
