from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.database import get_db
from app.auth.deps import require_user, require_permission
from app.auth.permissions import PERMISSIONS, DEFAULT_ROLES
from app.schemas.user import RoleCreate, RoleUpdate, PermissionInfo

logger = logging.getLogger("komajdon")
router = APIRouter(prefix="/api/roles", tags=["roles"])


async def _seed_default_roles(db: AsyncIOMotorDatabase):
    for name, config in DEFAULT_ROLES.items():
        existing = await db["_roles"].find_one({"name": name})
        if not existing:
            from datetime import datetime, timezone
            await db["_roles"].insert_one({
                "name": name,
                "description": config["description"],
                "permissions": config["permissions"],
                "is_default": config["is_default"],
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
            logger.info("Seeded default role: %s", name)


def _serialize_role(r: dict) -> dict:
    return {
        "id": str(r["_id"]),
        "name": r["name"],
        "description": r.get("description", ""),
        "permissions": r.get("permissions", []),
        "is_default": r.get("is_default", False),
        "created_at": r.get("created_at", ""),
    }


@router.get("/permissions")
async def list_permissions(
    user: dict = Depends(require_permission("roles:read")),
):
    return [
        PermissionInfo(key=k, description=v)
        for k, v in sorted(PERMISSIONS.items())
    ]


@router.get("/")
async def list_roles(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("roles:read")),
):
    roles = await db["_roles"].find().to_list(100)
    return [_serialize_role(r) for r in roles]


@router.post("/", status_code=201)
async def create_role(
    body: RoleCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("roles:create")),
):
    existing = await db["_roles"].find_one({"name": body.name})
    if existing:
        raise HTTPException(status_code=409, detail=f"Role '{body.name}' already exists")
    doc = {
        "name": body.name,
        "description": body.description,
        "permissions": body.permissions,
        "is_default": body.is_default,
        "created_at": body.name,
    }
    from datetime import datetime, timezone
    doc["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = await db["_roles"].insert_one(doc)
    return {"message": f"Role '{body.name}' created", "id": str(result.inserted_id)}


@router.get("/{role_id}")
async def get_role(
    role_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("roles:read")),
):
    try:
        oid = ObjectId(role_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid role ID")
    r = await db["_roles"].find_one({"_id": oid})
    if not r:
        raise HTTPException(status_code=404, detail="Role not found")
    return _serialize_role(r)


@router.put("/{role_id}")
async def update_role(
    role_id: str,
    body: RoleUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("roles:update")),
):
    try:
        oid = ObjectId(role_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid role ID")
    r = await db["_roles"].find_one({"_id": oid})
    if not r:
        raise HTTPException(status_code=404, detail="Role not found")
    if r.get("is_default"):
        raise HTTPException(status_code=400, detail="Cannot modify default roles")
    update = {}
    if body.name is not None:
        update["name"] = body.name
    if body.description is not None:
        update["description"] = body.description
    if body.permissions is not None:
        update["permissions"] = body.permissions
    if body.is_default is not None:
        update["is_default"] = body.is_default
    if update:
        await db["_roles"].update_one({"_id": oid}, {"$set": update})
    return {"message": f"Role '{r['name']}' updated"}


@router.delete("/{role_id}")
async def delete_role(
    role_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("roles:delete")),
):
    try:
        oid = ObjectId(role_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid role ID")
    r = await db["_roles"].find_one({"_id": oid})
    if not r:
        raise HTTPException(status_code=404, detail="Role not found")
    if r.get("is_default"):
        raise HTTPException(status_code=400, detail="Cannot delete default roles")
    await db["_roles"].delete_one({"_id": oid})
    return {"message": f"Role '{r['name']}' deleted"}
