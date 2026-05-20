from __future__ import annotations

import re
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.config import settings
from app.database import get_db
from app.schemas.user import (
    UserCreate, UserCreateManual, UserLogin, Token, RefreshTokenRequest,
    PasswordResetRequest, PasswordResetConfirm, VerifyEmailRequest,
    UserUpdateRole, UserUpdate,
)
from app.auth.jwt import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    create_verification_token, verify_verification_token,
    create_password_reset_token, verify_password_reset_token,
)
from app.auth.deps import require_user, require_permission
from app.auth.permissions import has_permission

logger = logging.getLogger("komajdon")
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _validate_password(password: str):
    if len(password) < settings.password_min_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must be at least {settings.password_min_length} characters",
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must contain at least one uppercase letter",
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must contain at least one lowercase letter",
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must contain at least one digit",
        )


async def _resolve_role_permissions(db: AsyncIOMotorDatabase, role_name: str) -> list[str]:
    role = await db["_roles"].find_one({"name": role_name})
    if role:
        return role.get("permissions", [])
    return ["api:access"]


def _serialize_user(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "role": user.get("role", "user"),
        "permissions": user.get("permissions", []),
        "email_verified": user.get("email_verified", False),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at", ""),
    }


async def _make_token_response(email: str, db: AsyncIOMotorDatabase) -> Token:
    access = create_access_token({"sub": email})
    refresh = create_refresh_token({"sub": email})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    await db["_refresh_tokens"].insert_one({
        "token": refresh,
        "email": email,
        "created_at": now,
    })
    user = await db.users.find_one({"email": email})
    return Token(
        access_token=access,
        refresh_token=refresh,
        user=_serialize_user(user) if user else None,
    )


# ── Public: Sign Up ────────────────────────────────


@router.post("/signup", response_model=Token)
async def signup(body: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    email = body.email.lower() if body.email else body.email
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    _validate_password(body.password)

    perms = await _resolve_role_permissions(db, "user")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    user = {
        "email": email,
        "password": hash_password(body.password),
        "role": "user",
        "permissions": perms,
        "email_verified": False,
        "is_active": True,
        "created_at": now,
    }
    await db.users.insert_one(user)

    verification_token = create_verification_token(body.email)
    import os
    if os.environ.get("KOMAJDON_ENV") == "development":
        logger.info(
            "User %s registered. Verify token (dev): %s",
            body.email, verification_token,
        )

    return await _make_token_response(email, db)


# ── Public: Sign In ────────────────────────────────


@router.post("/signin", response_model=Token)
async def signin(body: UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    email = body.email.lower() if body.email else body.email
    user = await db.users.find_one({"email": email})

    # Account lockout check
    if user and user.get("locked_until"):
        locked_until = user["locked_until"]
        if isinstance(locked_until, str):
            try:
                locked_until = datetime.fromisoformat(locked_until)
            except (ValueError, TypeError):
                locked_until = datetime.min.replace(tzinfo=timezone.utc)
        if locked_until > datetime.now(timezone.utc):
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked. Try again in {remaining} seconds.",
            )

    if not user or not verify_password(body.password, user["password"]):
        if user:
            await db.users.update_one(
                {"email": email},
                {"$inc": {"failed_attempts": 1}},
            )
            updated = await db.users.find_one({"email": email})
            fails = updated.get("failed_attempts", 0)
            if fails >= 5:
                lock_time = datetime.now(timezone.utc) + timedelta(minutes=15)
                await db.users.update_one(
                    {"email": email},
                    {"$set": {"locked_until": lock_time.isoformat(), "failed_attempts": 0}},
                )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Reset failed attempts on success
    await db.users.update_one(
        {"email": email},
        {"$set": {"failed_attempts": 0, "locked_until": None}},
    )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    return await _make_token_response(email, db)


# ── Public: Login (alias for signin) ───────────────


@router.post("/login", response_model=Token)
async def login(body: UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await signin(body, db)


# ── Public: Register (alias for signup) ────────────


@router.post("/register", response_model=Token)
async def register(body: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await signup(body, db)


# ── Token Refresh ──────────────────────────────────


@router.post("/refresh", response_model=Token)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    stored = await db["_refresh_tokens"].find_one({"token": body.refresh_token})
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    email = stored["email"]
    await db["_refresh_tokens"].delete_one({"token": body.refresh_token})

    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return await _make_token_response(email, db)


# ── Logout ─────────────────────────────────────────


@router.post("/logout")
async def logout(
    body: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    await db["_refresh_tokens"].delete_one({"token": body.refresh_token})
    return {"message": "Logged out"}


# ── Email Verification ─────────────────────────────


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    email = verify_verification_token(body.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )
    result = await db.users.update_one(
        {"email": email},
        {"$set": {"email_verified": True}},
    )
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(user: dict = Depends(require_user)):
    if user.get("email_verified"):
        return {"message": "Email already verified"}
    token = create_verification_token(user["email"])
    import os
    if os.environ.get("KOMAJDON_ENV") == "development":
        logger.info("Verify token for %s (dev): %s", user["email"], token)
    return {"message": "Verification email sent (dev: token logged)"}


# ── Password Reset ─────────────────────────────────


@router.post("/forgot-password")
async def forgot_password(
    body: PasswordResetRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user = await db.users.find_one({"email": body.email})
    if not user:
        return {"message": "If the email exists, a reset link has been sent"}
    token = create_password_reset_token(body.email)
    import os
    if os.environ.get("KOMAJDON_ENV") == "development":
        logger.info("Password reset token for %s (dev): %s", body.email, token)
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    body: PasswordResetConfirm,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    email = verify_password_reset_token(body.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    _validate_password(body.new_password)
    result = await db.users.update_one(
        {"email": email},
        {"$set": {"password": hash_password(body.new_password)}},
    )
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    await db["_refresh_tokens"].delete_many({"email": email})
    return {"message": "Password reset successfully"}


# ── Current User ───────────────────────────────────


@router.get("/me")
async def get_me(user: dict = Depends(require_user)):
    return _serialize_user(user)


# ── Admin: Manual User Creation ────────────────────


@router.post("/users", status_code=201)
async def create_user_manual(
    body: UserCreateManual,
    db: AsyncIOMotorDatabase = Depends(get_db),
    admin: dict = Depends(require_permission("users:create")),
):
    existing = await db.users.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    perms = body.permissions
    if not perms:
        perms = await _resolve_role_permissions(db, body.role)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    email = body.email.lower() if body.email else body.email
    user = {
        "email": email,
        "password": hash_password(body.password),
        "role": body.role,
        "permissions": perms,
        "email_verified": True,
        "is_active": True,
        "created_at": now,
    }
    result = await db.users.insert_one(user)
    return {
        "message": f"User '{email}' created",
        "user": _serialize_user({"_id": result.inserted_id, **user}),
    }


# ── Admin: User Management ─────────────────────────


@router.get("/users")
async def list_users(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("users:read")),
):
    users = await db.users.find().to_list(1000)
    return [_serialize_user(u) for u in users]


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_permission("users:read")),
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    u = await db.users.find_one({"_id": oid})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(u)


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: UserUpdateRole,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_permission("users:update")),
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    update = {"role": body.role}

    perms = body.permissions
    if not perms:
        perms = await _resolve_role_permissions(db, body.role)
    update["permissions"] = perms

    result = await db.users.update_one({"_id": oid}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"User updated to role '{body.role}'"}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_permission("users:update")),
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.users.update_one({"_id": oid}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User updated"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(require_permission("users:delete")),
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    u = await db.users.find_one({"_id": oid})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.get("role") == "admin" and u["email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Cannot delete another admin")
    if u["email"] == current_user["email"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    await db.users.delete_one({"_id": oid})
    await db["_refresh_tokens"].delete_many({"email": u["email"]})
    return {"message": f"User '{u['email']}' deleted"}
