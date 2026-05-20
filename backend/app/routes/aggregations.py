from __future__ import annotations

import copy
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.auth.deps import require_user
from shared.stage_builders import STAGE_BUILDERS, serialize_results

logger = logging.getLogger("komajdon")
router = APIRouter(prefix="/api/aggregations", tags=["aggregations"])

TEMPLATES = {
    "count_by_field": {
        "name": "Count by field",
        "stages": [
            {"type": "group", "params": {"_id": "$field_name", "count": {"$sum": 1}}},
            {"type": "sort", "params": {"count": -1}},
        ],
    },
    "average_by_field": {
        "name": "Average by field",
        "stages": [
            {
                "type": "group",
                "params": {
                    "_id": "$field_name",
                    "average": {"$avg": "$value_field"},
                    "count": {"$sum": 1},
                },
            },
            {"type": "sort", "params": {"count": -1}},
        ],
    },
    "latest_items": {
        "name": "Latest items",
        "stages": [
            {"type": "sort", "params": {"_id": -1}},
            {"type": "limit", "params": {"limit": 10}},
        ],
    },
    "group_and_lookup": {
        "name": "Group with relation lookup",
        "stages": [
            {
                "type": "lookup",
                "params": {
                    "from": "related_collection",
                    "localField": "local_field",
                    "foreignField": "_id",
                    "as": "related",
                },
            },
            {"type": "unwind", "params": {"field": "related"}},
            {
                "type": "group",
                "params": {
                    "_id": "$related.name",
                    "count": {"$sum": 1},
                },
            },
        ],
    },
}


@router.get("/templates")
async def list_templates():
    return [{"id": k, **v} for k, v in TEMPLATES.items()]


SYSTEM_COLLECTIONS = {"users", "_schemas", "_roles", "_pipelines", "_api_keys", "_refresh_tokens", "_compositions", "_projects"}


@router.post("/run/{collection}")
async def run_aggregation(
    collection: str,
    template: str = Query(...),
    field_name: str = Query(""),
    value_field: str = Query(""),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    if collection in SYSTEM_COLLECTIONS:
        raise HTTPException(status_code=403, detail="Cannot aggregate over system collections")
    if template not in TEMPLATES:
        raise HTTPException(status_code=400, detail="Unknown template")

    raw_stages = copy.deepcopy(TEMPLATES[template]["stages"])

    pipeline = []
    for stage in raw_stages:
        builder = STAGE_BUILDERS.get(stage["type"])
        if not builder:
            continue
        params = dict(stage["params"])
        for k, v in list(params.items()):
            if isinstance(v, str):
                params[k] = v.replace("field_name", field_name).replace("value_field", value_field)
            elif isinstance(v, dict):
                for sk, sv in list(v.items()):
                    if isinstance(sv, str):
                        v[sk] = sv.replace("field_name", field_name).replace("value_field", value_field)
        try:
            pipeline.append(builder(params))
        except Exception:
            logger.warning("Failed to build stage '%s' in template '%s'", stage["type"], template)
            continue

    if not pipeline:
        return {"results": []}

    result = await db[collection].aggregate(pipeline).to_list(1000)
    return {"results": serialize_results(result)}
