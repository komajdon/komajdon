from __future__ import annotations

from datetime import datetime, timezone

import base64
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId, errors as bson_errors

logger = logging.getLogger("komajdon")

from app.database import get_db
from app.schemas.model_schema import ModelSchema, FieldDefinition
from app.auth.deps import get_current_user, require_user
from app.auth.permissions import collection_permission, has_permission
from app.auth.projects import optional_project
from app.websocket import manager
from app.cache import cache

router = APIRouter()
_registered_schemas: dict[str, ModelSchema] = {}

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")

import re

# Dangerous MongoDB operators that must never come from user input
BANNED_PREFIXES = ("$where", "$function", "$accumulator", "$expr")


def _sanitize_regex(v: str) -> str:
    """Limit regex length and reject ReDoS-prone patterns."""
    if len(v) > 200:
        raise HTTPException(status_code=400, detail="Regex pattern too long (max 200 chars)")
    if "(a+" in v or "(." in v:
        raise HTTPException(status_code=400, detail="Potentially dangerous regex pattern rejected")
    return v


def _sanitize_filter_value(value) -> object:
    """Strip banned MongoDB operators from filter values."""
    if isinstance(value, dict):
        for key in list(value):
            if any(key.startswith(p) for p in BANNED_PREFIXES):
                raise HTTPException(status_code=400, detail=f"Filter operator '{key}' is not allowed")
            value[key] = _sanitize_filter_value(value[key])
    elif isinstance(value, list):
        value = [_sanitize_filter_value(v) for v in value]
    return value


FILTER_OPS = {
    "eq": lambda v: _sanitize_filter_value(v),
    "ne": lambda v: _sanitize_filter_value({"$ne": v}),
    "gt": lambda v: _sanitize_filter_value({"$gt": v}),
    "gte": lambda v: _sanitize_filter_value({"$gte": v}),
    "lt": lambda v: _sanitize_filter_value({"$lt": v}),
    "lte": lambda v: _sanitize_filter_value({"$lte": v}),
    "in": lambda v: _sanitize_filter_value({"$in": v if isinstance(v, list) else [v]}),
    "nin": lambda v: _sanitize_filter_value({"$nin": v if isinstance(v, list) else [v]}),
    "regex": lambda v: _sanitize_filter_value({"$regex": _sanitize_regex(str(v)), "$options": "i"}),
    "contains": lambda v: _sanitize_filter_value({"$regex": _sanitize_regex(str(v)), "$options": "i"}),
    "near": lambda v: _sanitize_filter_value(_parse_geo_near(v)),
    "geo_within": lambda v: _sanitize_filter_value(_parse_geo_within(v)),
    "geo_intersects": lambda v: _sanitize_filter_value(_parse_geo_intersects(v)),
}


def _parse_geo_near(v: str) -> dict:
    parts = v.split(",")
    if len(parts) >= 3:
        return {"$near": {"$geometry": {"type": "Point", "coordinates": [float(parts[0]), float(parts[1])]}, "$maxDistance": float(parts[2])}}
    return {"$near": {"$geometry": {"type": "Point", "coordinates": [0, 0]}}}


def _parse_geo_within(v: str) -> dict:
    coords = [[float(x) for x in p.split(":")] for p in v.split(";")]
    return {"$geoWithin": {"$geometry": {"type": "Polygon", "coordinates": [coords]}}}


def _parse_geo_intersects(v: str) -> dict:
    coords = [[float(x) for x in p.split(":")] for p in v.split(";")]
    return {"$geoIntersects": {"$geometry": {"type": "Polygon", "coordinates": [coords]}}}


def _apply_owner_filter(query: dict, schema: ModelSchema, user: dict | None) -> dict:
    if not schema.auth_protected:
        return query
    if user and user.get("role") == "admin":
        return query
    owner_id = str(user["_id"]) if user else None
    if "$and" not in query:
        query["$and"] = []
    query["$and"].append({"owner_id": owner_id})
    return query


def _apply_soft_delete_filter(query: dict, include_deleted: bool = False) -> dict:
    if include_deleted:
        return query
    if "$and" not in query:
        query["$and"] = []
    query["$and"].append({"deleted_at": None})
    return query


def _serialize(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def _encode_cursor(item: dict, sort_field: str = "_id") -> str:
    val = item.get(sort_field, item.get("_id", ""))
    return base64.urlsafe_b64encode(json.dumps({"val": val, "sf": sort_field}).encode()).decode()


def _decode_cursor(cursor: str) -> tuple:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return data.get("val"), data.get("sf", "_id")
    except Exception:
        return None, "_id"


def _build_filter_query(raw_filters: list[str], schema: ModelSchema) -> dict:
    query: dict = {}
    field_names = {f.name for f in schema.fields}
    for expr in raw_filters:
        parts = expr.split("__", 2)
        if len(parts) == 2:
            field, value = parts
            op = "eq"
        elif len(parts) == 3:
            field, op, value = parts
        else:
            continue
        if field not in field_names:
            continue
        if op in FILTER_OPS:
            query[field] = FILTER_OPS[op](value)
    return query


def _cache_parts(collection: str, user: dict | None, extra: str = "") -> list[str]:
    uid = str(user["_id"]) if user else "anon"
    return [collection, uid, extra]


async def _validate_unique(
    db: AsyncIOMotorDatabase,
    collection: str,
    field: FieldDefinition,
    value: object,
    exclude_id: str | None = None,
) -> None:
    if not field.validation.unique or value is None:
        return
    q = {field.name: value}
    if exclude_id:
        try:
            q["_id"] = {"$ne": ObjectId(exclude_id)}
        except bson_errors.InvalidId:
            pass
    existing = await db[collection].find_one(q)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Field '{field.name}' must be unique. Value '{value}' already exists.",
        )


async def _validate_schema(
    db: AsyncIOMotorDatabase,
    collection: str,
    data: dict,
    schema: ModelSchema,
    exclude_id: str | None = None,
) -> None:
    # Reject unknown fields not in schema
    known_fields = {f.name for f in schema.fields}
    internal_fields = {"owner_id", "created_at", "updated_at", "deleted_at", "_id"}
    extra = set(data.keys()) - known_fields - internal_fields
    if extra:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown fields: {', '.join(sorted(extra))}",
        )

    for f in schema.fields:
        val = data.get(f.name)
        if f.validation.required and val is None and f.name not in data:
            raise HTTPException(status_code=422, detail=f"Field '{f.name}' is required")
        if val is not None:
            if f.type == "string" and isinstance(val, str):
                if f.validation.min_length is not None and len(val) < f.validation.min_length:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Field '{f.name}' min length is {f.validation.min_length}",
                    )
                if f.validation.max_length is not None and len(val) > f.validation.max_length:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Field '{f.name}' max length is {f.validation.max_length}",
                    )
                if f.validation.pattern:
                    if len(f.validation.pattern) > 200:
                        raise HTTPException(status_code=422, detail=f"Pattern for '{f.name}' too long")
                    try:
                        compiled = re.compile(f.validation.pattern)
                    except re.error:
                        raise HTTPException(status_code=422, detail=f"Invalid regex pattern for '{f.name}'")
                    if not compiled.match(val):
                        raise HTTPException(
                            status_code=422,
                            detail=f"Field '{f.name}' does not match pattern {f.validation.pattern}",
                        )
                if f.validation.enum and val not in f.validation.enum:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Field '{f.name}' must be one of {f.validation.enum}",
                    )
            if f.type == "number":
                try:
                    num = float(val)  # type: ignore
                    if f.validation.minimum is not None and num < f.validation.minimum:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Field '{f.name}' minimum is {f.validation.minimum}",
                        )
                    if f.validation.maximum is not None and num > f.validation.maximum:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Field '{f.name}' maximum is {f.validation.maximum}",
                        )
                except (TypeError, ValueError):
                    pass
            await _validate_unique(db, collection, f, val, exclude_id)

    for f in schema.fields:
        if f.relation and f.relation.type in ("belongs_to", "has_one"):
            fk_val = data.get(f.relation.foreign_key or f"{f.relation.target_model}_id")
            if fk_val:
                try:
                    fk_doc = await db[f.relation.target_model].find_one(
                        {"_id": ObjectId(str(fk_val))}
                    )
                    if not fk_doc:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Referenced {f.relation.target_model} '{fk_val}' not found",
                        )
                except bson_errors.InvalidId:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Invalid reference ID for {f.relation.target_model}",
                    )


async def _list_items(
    collection: str,
    schema: ModelSchema,
    db: AsyncIOMotorDatabase,
    user: dict | None,
    skip: int = 0,
    limit: int = 100,
    sort: str | None = None,
    populate: str | None = None,
    fields: str | None = None,
    filters: list[str] = None,
    include_deleted: bool = False,
    cursor: str | None = None,
    search: str | None = None,
    agg_count: str | None = None,
    agg_sum: str | None = None,
):
    query = _build_filter_query(filters or [], schema)
    query = _apply_soft_delete_filter(query, include_deleted)
    query = _apply_owner_filter(query, schema, user)

    # Full-text search
    if search:
        if len(search) > 200:
            raise HTTPException(status_code=400, detail="Search query too long")
        query["$text"] = {"$search": search}

    # Aggregation shortcuts — return aggregated results directly
    if agg_count or agg_sum:
        pipeline = [{"$match": query}]
        group_stage = {"_id": None}
        if agg_count:
            group_stage[f"{agg_count}_count"] = {"$sum": 1}
        if agg_sum:
            for f in agg_sum.split(","):
                f = f.strip()
                group_stage[f"{f}_sum"] = {"$sum": f"${f}"}
        pipeline.append({"$group": group_stage})
        result = await db[collection].aggregate(pipeline).to_list(1000)
        return _serialize(result[0]) if result else {}, None

    projection = None
    if fields:
        projection = {f.strip(): 1 for f in fields.split(",") if f.strip()}
        projection["_id"] = 1

    mongo_cursor = db[collection].find(query, projection)

    if sort:
        parts = sort.split(",")
        sort_spec = []
        for p in parts:
            p = p.strip()
            if p.startswith("-"):
                sort_spec.append((p[1:], -1))
            else:
                sort_spec.append((p, 1))
        mongo_cursor = mongo_cursor.sort(sort_spec)
        sort_field = parts[0] if not parts[0].startswith("-") else parts[0][1:]
    else:
        mongo_cursor = mongo_cursor.sort("created_at", -1)
        sort_field = "created_at"

    if cursor:
        cursor_val, cursor_field = _decode_cursor(cursor)
        if cursor_val is not None:
            if sort and parts:
                is_desc = parts[0].startswith("-")
                cursor_op = "$lt" if is_desc else "$gt"
            else:
                cursor_op = "$lt"
            query[cursor_field] = {cursor_op: cursor_val}
            mongo_cursor = db[collection].find(query, projection)
            if sort:
                mongo_cursor = mongo_cursor.sort(sort_spec)
            else:
                mongo_cursor = mongo_cursor.sort("created_at", -1)
    else:
        mongo_cursor = mongo_cursor.skip(skip)

    mongo_cursor = mongo_cursor.limit(limit + 1)

    items = await mongo_cursor.to_list(limit + 1)
    has_next = len(items) > limit
    items = items[:limit]
    result = [_serialize(item) for item in items]

    next_cursor = None
    if has_next and result:
        next_cursor = _encode_cursor(result[-1], sort_field)

    if populate and schema.fields:
        rel_fields = {f.relation.target_model for f in schema.fields if f.relation}
        targets = [t.strip() for t in populate.split(",") if t.strip() in rel_fields]
        for item in result:
            for f in schema.fields:
                if f.relation and f.relation.target_model in targets:
                    fk_field = f.relation.foreign_key or f"{f.relation.target_model}_id"
                    fk_val = item.get(fk_field)
                    if fk_val:
                        rel_doc = await db[f.relation.target_model].find_one(
                            {"_id": ObjectId(str(fk_val))}
                        )
                        item[f.relation.target_model] = (
                            _serialize(rel_doc) if rel_doc else None
                        )

    return result, next_cursor


async def _create_item(
    collection: str,
    schema: ModelSchema,
    item: dict,
    db: AsyncIOMotorDatabase,
    user: dict | None,
):
    if schema.auth_protected:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth required"
            )
        item["owner_id"] = str(user["_id"])

    await _validate_schema(db, collection, item, schema)

    now = NOW()
    item["created_at"] = now
    item["updated_at"] = now
    item["deleted_at"] = None

    for f in schema.fields:
        if f.default is not None and f.name not in item:
            item[f.name] = f.default() if callable(f.default) else f.default

    result = await db[collection].insert_one(item)
    created = await db[collection].find_one({"_id": result.inserted_id})
    serialized = _serialize(created)

    cache.invalidate_prefix(f"api:{collection}")

    if schema.realtime_enabled:
        await manager.broadcast(collection, "create", serialized)

    return serialized


async def _get_item(
    collection: str,
    schema: ModelSchema,
    id: str,
    db: AsyncIOMotorDatabase,
    user: dict | None,
    populate: str | None = None,
    fields: str | None = None,
    include_deleted: bool = False,
):
    try:
        obj_id = ObjectId(id)
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    projection = None
    if fields:
        projection = {f.strip(): 1 for f in fields.split(",") if f.strip()}
        projection["_id"] = 1

    query: dict = {"_id": obj_id}
    query = _apply_soft_delete_filter(query, include_deleted)
    query = _apply_owner_filter(query, schema, user)
    item = await db[collection].find_one(query, projection)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    result = _serialize(item)

    if populate and schema.fields:
        rel_fields = {f.relation.target_model for f in schema.fields if f.relation}
        targets = [t.strip() for t in populate.split(",") if t.strip() in rel_fields]
        for f in schema.fields:
            if f.relation and f.relation.target_model in targets:
                fk_field = f.relation.foreign_key or f"{f.relation.target_model}_id"
                fk_val = result.get(fk_field)
                if fk_val:
                    try:
                        rel_doc = await db[f.relation.target_model].find_one(
                            {"_id": ObjectId(str(fk_val))}
                        )
                        result[f.relation.target_model] = (
                            _serialize(rel_doc) if rel_doc else None
                        )
                    except bson_errors.InvalidId:
                        pass

    return result


async def _update_item(
    collection: str,
    schema: ModelSchema,
    id: str,
    data: dict,
    db: AsyncIOMotorDatabase,
    user: dict | None,
):
    try:
        obj_id = ObjectId(id)
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    await _validate_schema(db, collection, data, schema, exclude_id=id)

    data["updated_at"] = NOW()

    query: dict = {"_id": obj_id}
    query = _apply_soft_delete_filter(query)
    query = _apply_owner_filter(query, schema, user)
    result = await db[collection].update_one(query, {"$set": data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    updated = await db[collection].find_one({"_id": obj_id})
    serialized = _serialize(updated)

    cache.invalidate_prefix(f"api:{collection}")

    if schema.realtime_enabled:
        await manager.broadcast(collection, "update", serialized)

    return serialized


async def _replace_item(
    collection: str,
    schema: ModelSchema,
    id: str,
    data: dict,
    db: AsyncIOMotorDatabase,
    user: dict | None,
):
    try:
        obj_id = ObjectId(id)
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    await _validate_schema(db, collection, data, schema, exclude_id=id)

    query: dict = {"_id": obj_id}
    query = _apply_soft_delete_filter(query)
    query = _apply_owner_filter(query, schema, user)
    doc = await db[collection].find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")

    data["_id"] = obj_id
    data["created_at"] = doc.get("created_at", NOW())
    data["updated_at"] = NOW()
    data["deleted_at"] = doc.get("deleted_at")
    if schema.auth_protected:
        data["owner_id"] = doc.get("owner_id")

    await db[collection].replace_one({"_id": obj_id}, data)
    serialized = _serialize({k: v for k, v in data.items() if k != "_id"})
    serialized["_id"] = str(obj_id)

    cache.invalidate_prefix(f"api:{collection}")

    if schema.realtime_enabled:
        await manager.broadcast(collection, "replace", serialized)

    return serialized


async def _soft_delete_item(
    collection: str,
    schema: ModelSchema,
    id: str,
    db: AsyncIOMotorDatabase,
    user: dict | None,
):
    try:
        obj_id = ObjectId(id)
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    query: dict = {"_id": obj_id}
    query = _apply_soft_delete_filter(query)
    query = _apply_owner_filter(query, schema, user)
    now = NOW()
    result = await db[collection].update_one(query, {"$set": {"deleted_at": now, "updated_at": now}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    cache.invalidate_prefix(f"api:{collection}")

    if schema.realtime_enabled:
        await manager.broadcast(collection, "delete", {"_id": id, "deleted_at": now})

    return {"message": "Deleted (soft)", "deleted_at": now}


async def _restore_item(
    collection: str,
    schema: ModelSchema,
    id: str,
    db: AsyncIOMotorDatabase,
    user: dict | None,
):
    try:
        obj_id = ObjectId(id)
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    query: dict = {"_id": obj_id}
    query = _apply_soft_delete_filter(query, include_deleted=True)
    query = _apply_owner_filter(query, schema, user)
    now = NOW()
    result = await db[collection].update_one(
        {"_id": obj_id, "deleted_at": {"$ne": None}},
        {"$set": {"deleted_at": None, "updated_at": now}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found or not deleted")

    cache.invalidate_prefix(f"api:{collection}")

    updated = await db[collection].find_one({"_id": obj_id})
    return _serialize(updated)


async def _hard_delete_item(
    collection: str,
    schema: ModelSchema,
    id: str,
    db: AsyncIOMotorDatabase,
    user: dict | None,
):
    try:
        obj_id = ObjectId(id)
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    query: dict = {"_id": obj_id}
    query = _apply_owner_filter(query, schema, user)
    result = await db[collection].delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    cache.invalidate_prefix(f"api:{collection}")

    if schema.realtime_enabled:
        await manager.broadcast(collection, "delete", {"_id": id})

    return {"message": "Permanently deleted"}


# ── Bulk Operations ────────────────────────────────────


async def _bulk_create(
    collection: str,
    schema: ModelSchema,
    items: list[dict],
    db: AsyncIOMotorDatabase,
    user: dict | None,
):
    created = []
    for item in items:
        if schema.auth_protected:
            item["owner_id"] = str(user["_id"]) if user else None
        now = NOW()
        item["created_at"] = now
        item["updated_at"] = now
        item["deleted_at"] = None
    if len(items) > 100:
        raise HTTPException(status_code=422, detail="Bulk create limited to 100 items")
    result = await db[collection].insert_many(items)
    for oid in result.inserted_ids:
        doc = await db[collection].find_one({"_id": oid})
        created.append(_serialize(doc))
    cache.invalidate_prefix(f"api:{collection}")
    if schema.realtime_enabled and created:
        await manager.broadcast(collection, "bulk_create", created)
    return created


async def _bulk_update(
    collection: str,
    schema: ModelSchema,
    ids: list[str],
    data: dict,
    db: AsyncIOMotorDatabase,
    user: dict | None,
):
    if len(ids) > 100:
        raise HTTPException(status_code=422, detail="Bulk update limited to 100 items")
    obj_ids = []
    for id_str in ids:
        try:
            obj_ids.append(ObjectId(id_str))
        except bson_errors.InvalidId:
            raise HTTPException(status_code=400, detail=f"Invalid ID: {id_str}")
    query = {"_id": {"$in": obj_ids}}
    query = _apply_owner_filter(query, schema, user)
    now = NOW()
    data["updated_at"] = now
    result = await db[collection].update_many(query, {"$set": data})
    cache.invalidate_prefix(f"api:{collection}")
    return {"message": f"Updated {result.modified_count} documents"}


async def _bulk_delete(
    collection: str,
    schema: ModelSchema,
    ids: list[str],
    hard: bool,
    db: AsyncIOMotorDatabase,
    user: dict | None,
):
    if len(ids) > 100:
        raise HTTPException(status_code=422, detail="Bulk delete limited to 100 items")
    obj_ids = []
    for id_str in ids:
        try:
            obj_ids.append(ObjectId(id_str))
        except bson_errors.InvalidId:
            raise HTTPException(status_code=400, detail=f"Invalid ID: {id_str}")
    query = {"_id": {"$in": obj_ids}}
    query = _apply_owner_filter(query, schema, user)
    if hard:
        result = await db[collection].delete_many(query)
    else:
        now = NOW()
        result = await db[collection].update_many(
            query, {"$set": {"deleted_at": now, "updated_at": now}}
        )
    cache.invalidate_prefix(f"api:{collection}")
    return {"message": f"{'Permanently deleted' if hard else 'Soft-deleted'} {result.deleted_count if hard else result.modified_count} documents"}


def _project_collection(collection: str, project: dict | None) -> str:
    if project:
        return f"{project['_id']}__{collection}"
    return collection


_registered_schemas_by_project: dict[str, dict[str, ModelSchema]] = {
    "global": {},
}


async def _resolve_project(
    x_project_id: str | None,
    db: AsyncIOMotorDatabase,
    user: dict | None = None,
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
            pass
    if not project:
        return None
    if user:
        from app.auth.projects import check_project_access
        await check_project_access(project, user)
    return project


def _store_schema(schema: ModelSchema, project: dict | None = None):
    key = str(project["_id"]) if project else "global"
    if key not in _registered_schemas_by_project:
        _registered_schemas_by_project[key] = {}
    _registered_schemas_by_project[key][schema.name] = schema


def _get_schema(schema_name: str, project: dict | None = None) -> ModelSchema | None:
    key = str(project["_id"]) if project else "global"
    return _registered_schemas_by_project.get(key, {}).get(schema_name)


async def generate_routes_for_schema(schema: ModelSchema, app_router=None, project: dict | None = None):
    target = app_router or router
    api_collection = schema.name
    prefix = f"/api/{api_collection}"

    read_perm = collection_permission(api_collection, "read")
    create_perm = collection_permission(api_collection, "create")
    update_perm = collection_permission(api_collection, "update")
    delete_perm = collection_permission(api_collection, "delete")

    _store_schema(schema, project)

    # ── List ──────────────────────────────────────────────
    async def list_endpoint(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        sort: str | None = Query(None, description="field or -field for desc, comma-sep"),
        populate: str | None = Query(None, description="Comma-separated relations to populate"),
        fields: str | None = Query(None, description="Projection: field names comma-sep"),
        filter: list[str] = Query([], alias="filter", description="field__op=value"),
        include_deleted: bool = Query(False, description="Include soft-deleted docs"),
        cursor: str | None = Query(None, description="Cursor for cursor-based pagination"),
        search: str | None = Query(None, description="Full-text search query"),
        agg_count: str | None = Query(None, description="Aggregation: count field (e.g. 'status')"),
        agg_sum: str | None = Query(None, description="Aggregation: sum field(s) (e.g. 'price,quantity')"),
        x_project_id: str | None = Header(None, alias="X-Project-Id"),
        user: dict | None = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        if not has_permission(user, read_perm):
            raise HTTPException(status_code=403, detail=f"Missing permission: {read_perm}")
        proj = await _resolve_project(x_project_id, db, user) if x_project_id else None
        coll = _project_collection(api_collection, proj)
        sch = _get_schema(api_collection, proj) or schema
        is_agg = bool(agg_count or agg_sum)
        parts = _cache_parts(coll, user, f"list_{skip}_{limit}_{sort}_{include_deleted}_{search}")
        cached = cache.get("api", *parts)
        if cached is not None and not cursor and not is_agg:
            return cached
        result, next_cursor = await _list_items(
            coll, sch, db, user,
            skip=skip, limit=limit, sort=sort,
            populate=populate, fields=fields,
            filters=filter, include_deleted=include_deleted,
            cursor=cursor, search=search,
            agg_count=agg_count, agg_sum=agg_sum,
        )
        if is_agg:
            return result
        if not cursor:
            cache.set("api", result, 10.0, *parts)
            return result
        return {"data": result, "next_cursor": next_cursor}

    # ── Create ────────────────────────────────────────────
    async def create_endpoint(
        item: dict,
        x_project_id: str | None = Header(None, alias="X-Project-Id"),
        user: dict | None = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        if not has_permission(user, create_perm):
            raise HTTPException(status_code=403, detail=f"Missing permission: {create_perm}")
        proj = await _resolve_project(x_project_id, db, user) if x_project_id else None
        coll = _project_collection(api_collection, proj)
        sch = _get_schema(api_collection, proj) or schema
        return await _create_item(coll, sch, item, db, user)

    # ── Get by ID ─────────────────────────────────────────
    async def get_endpoint(
        id: str,
        populate: str | None = Query(None),
        fields: str | None = Query(None),
        include_deleted: bool = Query(False),
        x_project_id: str | None = Header(None, alias="X-Project-Id"),
        user: dict | None = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        if not has_permission(user, read_perm):
            raise HTTPException(status_code=403, detail=f"Missing permission: {read_perm}")
        proj = await _resolve_project(x_project_id, db, user) if x_project_id else None
        coll = _project_collection(api_collection, proj)
        sch = _get_schema(api_collection, proj) or schema
        parts = _cache_parts(coll, user, f"get_{id}_{include_deleted}")
        cached = cache.get("api", *parts)
        if cached is not None:
            return cached
        result = await _get_item(
            coll, sch, id, db, user,
            populate=populate, fields=fields, include_deleted=include_deleted,
        )
        cache.set("api", result, 10.0, *parts)
        return result

    # ── Update (PATCH) ────────────────────────────────────
    async def update_endpoint(
        id: str,
        data: dict,
        x_project_id: str | None = Header(None, alias="X-Project-Id"),
        user: dict | None = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        if not has_permission(user, update_perm):
            raise HTTPException(status_code=403, detail=f"Missing permission: {update_perm}")
        proj = await _resolve_project(x_project_id, db, user) if x_project_id else None
        coll = _project_collection(api_collection, proj)
        sch = _get_schema(api_collection, proj) or schema
        return await _update_item(coll, sch, id, data, db, user)

    # ── Replace (PUT) ─────────────────────────────────────
    async def replace_endpoint(
        id: str,
        data: dict,
        x_project_id: str | None = Header(None, alias="X-Project-Id"),
        user: dict | None = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        if not has_permission(user, update_perm):
            raise HTTPException(status_code=403, detail=f"Missing permission: {update_perm}")
        proj = await _resolve_project(x_project_id, db, user) if x_project_id else None
        coll = _project_collection(api_collection, proj)
        sch = _get_schema(api_collection, proj) or schema
        return await _replace_item(coll, sch, id, data, db, user)

    # ── Soft Delete (DELETE) ──────────────────────────────
    async def delete_endpoint(
        id: str,
        hard: bool = Query(False, description="Permanently remove"),
        x_project_id: str | None = Header(None, alias="X-Project-Id"),
        user: dict | None = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        if not has_permission(user, delete_perm):
            raise HTTPException(status_code=403, detail=f"Missing permission: {delete_perm}")
        proj = await _resolve_project(x_project_id, db, user) if x_project_id else None
        coll = _project_collection(api_collection, proj)
        sch = _get_schema(api_collection, proj) or schema
        if hard:
            return await _hard_delete_item(coll, sch, id, db, user)
        return await _soft_delete_item(coll, sch, id, db, user)

    # ── Restore ───────────────────────────────────────────
    async def restore_endpoint(
        id: str,
        x_project_id: str | None = Header(None, alias="X-Project-Id"),
        user: dict | None = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        if not has_permission(user, delete_perm):
            raise HTTPException(status_code=403, detail=f"Missing permission: {delete_perm}")
        proj = await _resolve_project(x_project_id, db, user) if x_project_id else None
        coll = _project_collection(api_collection, proj)
        sch = _get_schema(api_collection, proj) or schema
        return await _restore_item(coll, sch, id, db, user)

    # ── Bulk routes ──────────────────────────────────────
    async def bulk_create_endpoint(
        items: list[dict],
        x_project_id: str | None = Header(None, alias="X-Project-Id"),
        user: dict | None = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        if not has_permission(user, create_perm):
            raise HTTPException(status_code=403, detail=f"Missing permission: {create_perm}")
        proj = await _resolve_project(x_project_id, db, user) if x_project_id else None
        coll = _project_collection(api_collection, proj)
        sch = _get_schema(api_collection, proj) or schema
        return await _bulk_create(coll, sch, items, db, user)

    async def bulk_update_endpoint(
        body: dict,
        x_project_id: str | None = Header(None, alias="X-Project-Id"),
        user: dict | None = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        if not has_permission(user, update_perm):
            raise HTTPException(status_code=403, detail=f"Missing permission: {update_perm}")
        proj = await _resolve_project(x_project_id, db, user) if x_project_id else None
        coll = _project_collection(api_collection, proj)
        sch = _get_schema(api_collection, proj) or schema
        ids = body.get("ids", [])
        data = body.get("data", {})
        return await _bulk_update(coll, sch, ids, data, db, user)

    async def bulk_delete_endpoint(
        body: dict,
        hard: bool = Query(False),
        x_project_id: str | None = Header(None, alias="X-Project-Id"),
        user: dict | None = Depends(get_current_user),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        if not has_permission(user, delete_perm):
            raise HTTPException(status_code=403, detail=f"Missing permission: {delete_perm}")
        proj = await _resolve_project(x_project_id, db, user) if x_project_id else None
        coll = _project_collection(api_collection, proj)
        sch = _get_schema(api_collection, proj) or schema
        ids = body.get("ids", [])
        return await _bulk_delete(coll, sch, ids, hard, db, user)

    # ── Register routes ───────────────────────────────────
    target.add_api_route(
        prefix,
        endpoint=list_endpoint, methods=["GET"],
        summary=f"List {api_collection}",
        tags=["dynamic"],
    )
    target.add_api_route(
        prefix,
        endpoint=create_endpoint, methods=["POST"],
        summary=f"Create {api_collection}",
        status_code=status.HTTP_201_CREATED,
        tags=["dynamic"],
    )
    target.add_api_route(
        f"{prefix}/{{id}}",
        endpoint=get_endpoint, methods=["GET"],
        summary=f"Get {api_collection} by ID",
        tags=["dynamic"],
    )
    target.add_api_route(
        f"{prefix}/{{id}}",
        endpoint=update_endpoint, methods=["PATCH"],
        summary=f"Update {api_collection}",
        tags=["dynamic"],
    )
    target.add_api_route(
        f"{prefix}/{{id}}",
        endpoint=replace_endpoint, methods=["PUT"],
        summary=f"Replace {api_collection}",
        tags=["dynamic"],
    )
    target.add_api_route(
        f"{prefix}/{{id}}",
        endpoint=delete_endpoint, methods=["DELETE"],
        summary=f"Delete {api_collection} (soft by default)",
        tags=["dynamic"],
    )
    target.add_api_route(
        f"{prefix}/{{id}}/restore",
        endpoint=restore_endpoint, methods=["POST"],
        summary=f"Restore soft-deleted {api_collection}",
        tags=["dynamic"],
    )
    target.add_api_route(
        f"{prefix}/bulk",
        endpoint=bulk_create_endpoint, methods=["POST"],
        summary=f"Bulk create {api_collection}",
        tags=["dynamic"],
    )
    target.add_api_route(
        f"{prefix}/bulk",
        endpoint=bulk_update_endpoint, methods=["PATCH"],
        summary=f"Bulk update {api_collection}",
        tags=["dynamic"],
    )
    target.add_api_route(
        f"{prefix}/bulk",
        endpoint=bulk_delete_endpoint, methods=["DELETE"],
        summary=f"Bulk delete {api_collection}",
        tags=["dynamic"],
    )

    _registered_schemas[api_collection] = schema


def get_registered_schemas() -> dict[str, ModelSchema]:
    return dict(_registered_schemas)


def get_project_schemas(project_id: str | None = None) -> dict[str, ModelSchema]:
    key = project_id or "global"
    return dict(_registered_schemas_by_project.get(key, {}))
