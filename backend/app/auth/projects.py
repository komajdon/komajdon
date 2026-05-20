from __future__ import annotations

from fastapi import Depends, HTTPException, Header, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.auth.deps import require_user


async def check_project_access(project: dict, user: dict) -> None:
    """Raise 403 if user is not admin, project owner, or project member."""
    if user.get("role") == "admin":
        return
    uid = str(user["_id"])
    if project.get("created_by") == uid:
        return
    if uid in project.get("members", []):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this project",
    )


async def require_project(
    x_project_id: str = Header(..., alias="X-Project-Id"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
) -> dict:
    project = await db["_projects"].find_one({"_id": x_project_id})
    if not project:
        project = await db["_projects"].find_one({"slug": x_project_id})
    if not project:
        from bson import ObjectId
        try:
            oid = ObjectId(x_project_id)
            project = await db["_projects"].find_one({"_id": oid})
        except Exception:
            pass
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await check_project_access(project, user)
    return project


async def optional_project(
    x_project_id: str | None = Header(None, alias="X-Project-Id"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
) -> dict | None:
    if not x_project_id:
        return None
    project = await db["_projects"].find_one({"_id": x_project_id})
    if not project:
        project = await db["_projects"].find_one({"slug": x_project_id})
    if not project:
        from bson import ObjectId
        try:
            oid = ObjectId(x_project_id)
            project = await db["_projects"].find_one({"_id": oid})
        except Exception:
            return None
    if not project:
        return None
    await check_project_access(project, user)
    return project
