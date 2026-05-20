from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.database import get_db
from app.auth.deps import require_permission
from app.middleware import reload_rate_limit_rules

logger = logging.getLogger("komajdon")
router = APIRouter(prefix="/api/rate-limits", tags=["rate-limits"])

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "*")


def _serialize(rule: dict) -> dict:
    return {
        "id": str(rule["_id"]),
        "endpoint": rule.get("endpoint", ""),
        "method": rule.get("method", "*"),
        "max_requests": rule.get("max_requests", 60),
        "window_seconds": rule.get("window_seconds", 60),
        "enabled": rule.get("enabled", True),
        "description": rule.get("description", ""),
        "created_at": rule.get("created_at", ""),
        "updated_at": rule.get("updated_at", ""),
    }


@router.get("/")
async def list_rules(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("system:settings")),
):
    rules = await db["_rate_limits"].find().sort("endpoint", 1).to_list(1000)
    return [_serialize(r) for r in rules]


@router.post("/", status_code=201)
async def create_rule(
    body: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("system:settings")),
):
    endpoint = body.get("endpoint", "").strip()
    method = body.get("method", "*").strip().upper()
    max_requests = body.get("max_requests", 60)
    window_seconds = body.get("window_seconds", 60)
    enabled = body.get("enabled", True)
    description = body.get("description", "")

    if not endpoint:
        raise HTTPException(status_code=422, detail="endpoint is required")
    if not endpoint.startswith("/"):
        raise HTTPException(status_code=422, detail="endpoint must start with /")
    if method not in METHODS:
        raise HTTPException(status_code=422, detail=f"method must be one of {METHODS}")
    if max_requests < 1 or max_requests > 10000:
        raise HTTPException(status_code=422, detail="max_requests must be 1-10000")
    if window_seconds < 1 or window_seconds > 86400:
        raise HTTPException(status_code=422, detail="window_seconds must be 1-86400")

    existing = await db["_rate_limits"].find_one({"endpoint": endpoint, "method": method})
    if existing:
        raise HTTPException(status_code=409, detail=f"Rule for {method} {endpoint} already exists")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc = {
        "endpoint": endpoint,
        "method": method,
        "max_requests": max_requests,
        "window_seconds": window_seconds,
        "enabled": enabled,
        "description": description,
        "created_at": now,
        "updated_at": now,
    }
    result = await db["_rate_limits"].insert_one(doc)
    await reload_rate_limit_rules(db)
    created = await db["_rate_limits"].find_one({"_id": result.inserted_id})
    return _serialize(created) if created else {**{k: v for k, v in doc.items() if k != "_id"}, "id": str(result.inserted_id)}


@router.put("/{rule_id}")
async def update_rule(
    rule_id: str,
    body: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("system:settings")),
):
    try:
        oid = ObjectId(rule_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid rule ID")

    existing = await db["_rate_limits"].find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")

    update = {}
    if "endpoint" in body:
        ep = body["endpoint"].strip()
        if not ep.startswith("/"):
            raise HTTPException(status_code=422, detail="endpoint must start with /")
        update["endpoint"] = ep
    if "method" in body:
        m = body["method"].strip().upper()
        if m not in METHODS:
            raise HTTPException(status_code=422, detail=f"method must be one of {METHODS}")
        update["method"] = m
    if "max_requests" in body:
        mr = body["max_requests"]
        if mr < 1 or mr > 10000:
            raise HTTPException(status_code=422, detail="max_requests must be 1-10000")
        update["max_requests"] = mr
    if "window_seconds" in body:
        ws = body["window_seconds"]
        if ws < 1 or ws > 86400:
            raise HTTPException(status_code=422, detail="window_seconds must be 1-86400")
        update["window_seconds"] = ws
    if "enabled" in body:
        update["enabled"] = bool(body["enabled"])
    if "description" in body:
        update["description"] = body.get("description", "")

    update["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    await db["_rate_limits"].update_one({"_id": oid}, {"$set": update})
    await reload_rate_limit_rules(db)

    updated = await db["_rate_limits"].find_one({"_id": oid})
    return _serialize(updated)


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("system:settings")),
):
    try:
        oid = ObjectId(rule_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid rule ID")

    result = await db["_rate_limits"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")

    await reload_rate_limit_rules(db)
    return {"message": "Rule deleted"}
