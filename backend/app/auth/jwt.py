from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=13)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _make_token(data: dict, expires_minutes: int) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": secrets.token_urlsafe(16),
    })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(data: dict) -> str:
    return _make_token(data, settings.access_token_expire_minutes)


def create_refresh_token(data: dict) -> str:
    token_str = secrets.token_urlsafe(48)
    return token_str


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm], options={"verify_exp": True})
    except JWTError:
        return None


def create_verification_token(email: str) -> str:
    return _make_token({"sub": email, "purpose": "email_verify"}, 60 * 24 * 7)


def verify_verification_token(token: str) -> str | None:
    payload = decode_token(token)
    if payload and payload.get("purpose") == "email_verify":
        return payload.get("sub")
    return None


def create_password_reset_token(email: str) -> str:
    return _make_token({"sub": email, "purpose": "password_reset"}, 60)


def verify_password_reset_token(token: str) -> str | None:
    payload = decode_token(token)
    if payload and payload.get("purpose") == "password_reset":
        return payload.get("sub")
    return None
