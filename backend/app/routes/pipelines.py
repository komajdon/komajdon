from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import BaseModel

from app.database import get_db
from app.auth.deps import require_user
from app.auth.projects import optional_project
from app.schemas.model_schema import AggregationPipeline, PipelineOut
from shared.stage_builders import build_pipeline, serialize_results

logger = logging.getLogger("komajdon")
router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])
_aggregation_registry: dict[str, dict] = {}


class ExportPipelineRequest(BaseModel):
    expose_as_api: bool = False
    api_method: str = "GET"
    api_path_template: str = "/api/aggregated/{name}"


@router.post("/")
async def create_pipeline(
    body: AggregationPipeline,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    from datetime import datetime, timezone
    doc = {
        "name": body.name,
        "collection": body.collection,
        "stages": [s.model_dump() for s in body.stages],
        "expose_as_api": False,
        "api_method": "GET",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if project:
        doc["project_id"] = str(project["_id"])
    result = await db["_pipelines"].insert_one(doc)
    return {
        "message": f"Pipeline '{body.name}' created",
        "id": str(result.inserted_id),
    }


@router.get("/")
async def list_pipelines(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    query = {}
    if project:
        query["project_id"] = str(project["_id"])
    pipelines = await db["_pipelines"].find(query).to_list(1000)
    return [
        PipelineOut(
            _id=str(p["_id"]),
            name=p["name"],
            collection=p.get("collection", ""),
            stages=p.get("stages", []),
            created_at=p.get("created_at", ""),
        )
        for p in pipelines
    ]


@router.get("/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    try:
        oid = ObjectId(pipeline_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    query: dict = {"_id": oid}
    if project:
        query["project_id"] = str(project["_id"])
    p = await db["_pipelines"].find_one(query)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return PipelineOut(
        _id=str(p["_id"]),
        name=p["name"],
        collection=p.get("collection", ""),
        stages=p.get("stages", []),
        created_at=p.get("created_at", ""),
    )


@router.put("/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    body: AggregationPipeline,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    try:
        oid = ObjectId(pipeline_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    query: dict = {"_id": oid}
    if project:
        query["project_id"] = str(project["_id"])
    existing = await db["_pipelines"].find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    updated = {
        "name": body.name,
        "collection": body.collection,
        "stages": [s.model_dump() for s in body.stages],
        "expose_as_api": existing.get("expose_as_api", False),
        "api_method": existing.get("api_method", "GET"),
        "created_at": existing.get("created_at", body.name),
    }
    if project:
        updated["project_id"] = str(project["_id"])
    elif existing.get("project_id"):
        updated["project_id"] = existing["project_id"]
    await db["_pipelines"].replace_one({"_id": oid}, updated)
    _re_register_aggregation(body.name, updated, request.app)
    return {"message": f"Pipeline '{body.name}' updated"}


@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    try:
        oid = ObjectId(pipeline_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    query: dict = {"_id": oid}
    if project:
        query["project_id"] = str(project["_id"])
    p = await db["_pipelines"].find_one(query)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    _aggregation_registry.pop(p.get("name", ""), None)
    await db["_pipelines"].delete_one({"_id": oid})
    return {"message": "Pipeline deleted"}


@router.post("/{pipeline_id}/expose")
async def expose_pipeline(
    pipeline_id: str,
    body: ExportPipelineRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    try:
        oid = ObjectId(pipeline_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    query: dict = {"_id": oid}
    if project:
        query["project_id"] = str(project["_id"])
    p = await db["_pipelines"].find_one(query)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    expose = body.expose_as_api
    api_method = body.api_method.upper()

    await db["_pipelines"].update_one(
        {"_id": oid},
        {"$set": {"expose_as_api": expose, "api_method": api_method}},
    )

    if expose:
        _register_aggregation_route(
            name=p["name"],
            collection=p["collection"],
            stages=p.get("stages", []),
            method=api_method,
            app=request.app,
        )
        path = body.api_path_template.replace("{name}", p["name"])
        return {"message": f"Pipeline exposed at {path}", "path": path}
    else:
        _aggregation_registry.pop(p["name"], None)
        return {"message": "Pipeline unexposed"}


@router.post("/run/{pipeline_id}")
async def run_pipeline(
    pipeline_id: str,
    params: dict = {},
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
    project: dict | None = Depends(optional_project),
):
    try:
        oid = ObjectId(pipeline_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    query: dict = {"_id": oid}
    if project:
        query["project_id"] = str(project["_id"])
    p = await db["_pipelines"].find_one(query)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    pipeline = build_pipeline(p.get("stages", []), params)
    collection = p.get("collection", "")
    if not collection.startswith("_") and not collection.isalnum() and not all(c.isalnum() or c == '_' for c in collection):
        raise HTTPException(status_code=400, detail="Invalid collection name")
    if not collection:
        raise HTTPException(status_code=422, detail="Pipeline has no target collection")

    result = await db[collection].aggregate(pipeline).to_list(5000)
    return {"results": serialize_results(result)}


def _register_aggregation_route(
    name: str, collection: str, stages: list, method: str, app
):
    async def endpoint(
        params: dict = {},
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        pipeline = build_pipeline(stages, params)
        result = await db[collection].aggregate(pipeline).to_list(5000)
        return {"results": serialize_results(result)}

    app.add_api_route(
        f"/api/aggregated/{name}",
        endpoint=endpoint,
        methods=[method],
        summary=f"Aggregated API: {name}",
        tags=["aggregated"],
    )
    _aggregation_registry[name] = {"collection": collection, "stages": stages}


def _re_register_aggregation(name: str, doc: dict, app):
    _aggregation_registry.pop(name, None)
    if doc.get("expose_as_api"):
        _register_aggregation_route(
            name=doc["name"],
            collection=doc["collection"],
            stages=doc.get("stages", []),
            method=doc.get("api_method", "GET"),
            app=app,
        )


def get_aggregation_registry() -> dict:
    return dict(_aggregation_registry)
