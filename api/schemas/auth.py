from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class SetupRequest(BaseModel):
    setup_key: str
    email: EmailStr
    password: str
    password_confirm: str


class RecoveryRequest(BaseModel):
    setup_key: str
    password: str
    password_confirm: str


class ClaimRequest(BaseModel):
    email: EmailStr
    password: str
    password_confirm: str


class SetupStatusResponse(BaseModel):
    needs_setup: bool
    reason: str


class UserSession(BaseModel):
    user_id: int
    username: str
    role: str
