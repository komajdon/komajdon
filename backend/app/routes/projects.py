from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.database import get_db
from app.auth.deps import require_user
from app.auth.projects import check_project_access
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = logging.getLogger("komajdon")
router = APIRouter(prefix="/api/projects", tags=["projects"])


def _serialize(p: dict) -> dict:
    return {
        "id": str(p["_id"]),
        "name": p["name"],
        "slug": p["slug"],
        "description": p.get("description", ""),
        "created_by": p.get("created_by", ""),
        "created_at": p.get("created_at", ""),
    }


@router.get("/", status_code=200)
async def list_projects(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    if user.get("role") == "admin":
        query = {}
    else:
        query = {
            "$or": [{"created_by": str(user["_id"])}, {"members": str(user["_id"])}]
        }
    projects = await db["_projects"].find(query).to_list(100)
    return [_serialize(p) for p in projects]


@router.post("/", status_code=201)
async def create_project(
    body: ProjectCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    existing = await db["_projects"].find_one({"slug": body.slug})
    if existing:
        raise HTTPException(status_code=409, detail=f"Project slug '{body.slug}' already exists")
    doc = {
        "name": body.name,
        "slug": body.slug,
        "description": body.description,
        "created_by": str(user["_id"]),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    result = await db["_projects"].insert_one(doc)
    return {"message": f"Project '{body.name}' created", "id": str(result.inserted_id)}


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    p = await db["_projects"].find_one({"_id": oid})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await check_project_access(p, user)
    return _serialize(p)


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    p = await db["_projects"].find_one({"_id": oid})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await check_project_access(p, user)
    update = {}
    if body.name is not None:
        update["name"] = body.name
    if body.description is not None:
        update["description"] = body.description
    if update:
        await db["_projects"].update_one({"_id": oid}, {"$set": update})
    return {"message": f"Project updated"}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    p = await db["_projects"].find_one({"_id": oid})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await check_project_access(p, user)
    result = await db["_projects"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}
