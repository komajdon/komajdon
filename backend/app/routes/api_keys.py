from __future__ import annotations

import secrets
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.database import get_db
from app.auth.deps import require_user, require_permission

logger = logging.getLogger("komajdon")
router = APIRouter(prefix="/api/keys", tags=["api-keys"])


def _serialize_key(k: dict) -> dict:
    return {
        "id": str(k["_id"]),
        "name": k.get("name", ""),
        "key_preview": k.get("key", "")[:12] + "..." if k.get("key") else "",
        "role": k.get("role", "viewer"),
        "permissions": k.get("permissions", []),
        "is_active": k.get("is_active", True),
        "last_used_at": k.get("last_used_at"),
        "created_at": k.get("created_at", ""),
    }


@router.post("/", status_code=201)
async def create_api_key(
    name: str = Query(..., description="A name for this key"),
    role: str = Query("viewer", description="Role to assign"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("api:access")),
):
    role_doc = await db["_roles"].find_one({"name": role})
    target_perms = role_doc.get("permissions", ["api:access", "*:read"]) if role_doc else ["api:access", "*:read"]

    from app.auth.permissions import has_permission
    for p in target_perms:
        if not has_permission(user, p):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You lack permission '{p}' required for role '{role}'",
            )

    raw_key = f"kj_{secrets.token_urlsafe(32)}"
    hashed_key = secrets.token_urlsafe(48)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc = {
        "name": name,
        "key": hashed_key,
        "role": role,
        "permissions": target_perms,
        "user_id": str(user["_id"]),
        "is_active": True,
        "last_used_at": None,
        "created_at": now,
    }
    result = await db["_api_keys"].insert_one(doc)

    # Store a key hash so DB compromise doesn't leak usable keys
    from app.auth.jwt import hash_password
    key_hash = hash_password(raw_key)
    await db["_api_keys"].update_one({"_id": result.inserted_id}, {"$set": {"key_hash": key_hash}})

    return {
        "message": f"API key '{name}' created",
        "id": str(result.inserted_id),
        "key": raw_key,
        "key_preview": raw_key[:12] + "...",
    }


@router.get("/")
async def list_api_keys(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("api:access")),
):
    keys = await db["_api_keys"].find({"user_id": str(user["_id"])}).to_list(100)
    return [_serialize_key(k) for k in keys]


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("api:access")),
):
    try:
        oid = ObjectId(key_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid key ID")
    result = await db["_api_keys"].delete_one({"_id": oid, "user_id": str(user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key deleted"}
