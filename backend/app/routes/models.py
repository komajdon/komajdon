from __future__ import annotations

import json
import logging

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.schemas.model_schema import ModelSchema, ModelSchemaOut, GenerateRequest
from app.auth.deps import require_user, require_permission
from app.auth.projects import optional_project
from app.routes.dynamic import generate_routes_for_schema

logger = logging.getLogger("komajdon")
router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/")
async def list_models(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    query = {}
    if project:
        query["project_id"] = str(project["_id"])
    schemas = await db["_schemas"].find(query).to_list(1000)
    return [
        ModelSchemaOut(
            _id=str(s["_id"]),
            name=s["name"],
            fields=s.get("fields", []),
            indexes=s.get("indexes", []),
            auth_protected=s.get("auth_protected", False),
            realtime_enabled=s.get("realtime_enabled", False),
            created_at=s.get("created_at", ""),
        )
        for s in schemas
    ]


@router.get("/{name}")
async def get_model(
    name: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    q = {"name": name}
    if project:
        q["project_id"] = str(project["_id"])
    s = await db["_schemas"].find_one(q)
    if not s:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelSchemaOut(
        _id=str(s["_id"]),
        name=s["name"],
        fields=s.get("fields", []),
        indexes=s.get("indexes", []),
        auth_protected=s.get("auth_protected", False),
        realtime_enabled=s.get("realtime_enabled", False),
        created_at=s.get("created_at", ""),
    )


async def _ensure_indexes(db: AsyncIOMotorDatabase, collection: str, body: GenerateRequest):
    for idx in body.indexes:
        try:
            await db[collection].create_index([(idx.field, idx.direction)], unique=idx.unique)
        except Exception as e:
            logger.warning("Failed to create index '%s' on '%s': %s", idx.field, collection, e)
    for f in body.fields:
        if f.indexed:
            try:
                await db[collection].create_index(f.name)
            except Exception as e:
                logger.warning("Failed to create index on field '%s': %s", f.name, e)
        if f.validation.unique:
            try:
                await db[collection].create_index(f.name, unique=True)
            except Exception as e:
                logger.warning("Failed to create unique index on field '%s': %s", f.name, e)


@router.post("/")
async def create_model(
    body: GenerateRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    query = {"name": body.name}
    if project:
        query["project_id"] = str(project["_id"])
    existing = await db["_schemas"].find_one(query)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{body.name}' already exists" + (" in this project" if project else ""),
        )
    schema_doc = {
        "name": body.name,
        "fields": [f.model_dump() for f in body.fields],
        "indexes": [i.model_dump() for i in body.indexes],
        "auth_protected": body.auth_protected,
        "realtime_enabled": body.realtime_enabled,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if project:
        schema_doc["project_id"] = str(project["_id"])
    result = await db["_schemas"].insert_one(schema_doc)

    model = ModelSchema(
        name=body.name,
        fields=body.fields,
        indexes=body.indexes,
        auth_protected=body.auth_protected,
        realtime_enabled=body.realtime_enabled,
    )

    await _ensure_indexes(db, body.name, body)
    await generate_routes_for_schema(model, request.app, project=project)

    return {
        "message": f"Model '{body.name}' created with API endpoints",
        "id": str(result.inserted_id),
    }


@router.put("/{name}")
async def update_model(
    name: str,
    body: GenerateRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    q = {"name": name}
    if project:
        q["project_id"] = str(project["_id"])
    existing = await db["_schemas"].find_one(q)
    if not existing:
        raise HTTPException(status_code=404, detail="Model not found")

    # Preserve existing data: read docs, drop, recreate indexes, re-insert
    old_docs = await db[name].find().to_list(10000)
    old_ids = {str(d["_id"]) for d in old_docs}

    await db[name].drop()
    await _ensure_indexes(db, body.name, body)

    if old_docs:
        cleaned = [{k: v for k, v in doc.items() if k != "_id"} for doc in old_docs]
        await db[body.name].insert_many(cleaned)
        logger.info("Migrated %d documents to updated schema for '%s'", len(old_docs), body.name)

    updated_doc = {
        "name": body.name,
        "fields": [f.model_dump() for f in body.fields],
        "indexes": [i.model_dump() for i in body.indexes],
        "auth_protected": body.auth_protected,
        "realtime_enabled": body.realtime_enabled,
        "created_at": existing.get("created_at", body.name),
    }
    await db["_schemas"].replace_one({"name": name}, updated_doc)

    model = ModelSchema(
        name=body.name,
        fields=body.fields,
        indexes=body.indexes,
        auth_protected=body.auth_protected,
        realtime_enabled=body.realtime_enabled,
    )
    await generate_routes_for_schema(model, request.app)

    return {
        "message": f"Model '{name}' updated",
        "collection_recreated": True,
        "migrated_docs": len(old_docs),
    }


@router.delete("/{name}")
async def delete_model(
    name: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    coll = f"{project['_id']}__{name}" if project else name
    await db[coll].drop()
    q = {"name": name}
    if project:
        q["project_id"] = str(project["_id"])
    result = await db["_schemas"].delete_one(q)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": f"Model '{name}' deleted", "collection_dropped": True}


@router.get("/{name}/export")
async def export_schema(
    name: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_permission("models:read")),
):
    s = await db["_schemas"].find_one({"name": name})
    if not s:
        raise HTTPException(status_code=404, detail="Model not found")
    doc = {
        "name": s["name"],
        "fields": s.get("fields", []),
        "indexes": s.get("indexes", []),
        "auth_protected": s.get("auth_protected", False),
        "realtime_enabled": s.get("realtime_enabled", False),
    }
    return Response(
        content=json.dumps(doc, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}-schema.json"'},
    )


@router.post("/import")
async def import_schema(
    body: dict,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    name = body.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="Schema must have a name")
    existing = await db["_schemas"].find_one({"name": name})
    if existing:
        raise HTTPException(status_code=409, detail=f"Model '{name}' already exists")

    from app.schemas.model_schema import FieldDefinition, IndexSpec
    fields = [FieldDefinition(**f) for f in body.get("fields", [])]
    indexes = [IndexSpec(**i) for i in body.get("indexes", [])]

    req = GenerateRequest(
        name=name,
        fields=fields,
        indexes=indexes,
        auth_protected=body.get("auth_protected", False),
        realtime_enabled=body.get("realtime_enabled", False),
    )

    return await create_model(req, request, db, user)
