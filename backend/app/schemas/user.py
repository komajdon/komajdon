from __future__ import annotations

import re
from pydantic import BaseModel, Field, field_validator


EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class UserCreate(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError('Invalid email format')
        return v


class UserCreateManual(BaseModel):
    email: str
    password: str
    role: str = "user"
    permissions: list[str] = []


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"
    user: dict | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError('Invalid email format')
        return v


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class UserUpdateRole(BaseModel):
    role: str
    permissions: list[str] = []


class UserUpdate(BaseModel):
    email: str | None = None
    is_active: bool | None = None
    email_verified: bool | None = None


# ── Role Schemas ────────────────────────────────────


class RoleCreate(BaseModel):
    name: str
    description: str = ""
    permissions: list[str] = []
    is_default: bool = False


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None
    is_default: bool | None = None


# ── Permission Schemas ─────────────────────────────


class PermissionInfo(BaseModel):
    key: str
    description: str
