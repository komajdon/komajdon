from __future__ import annotations

import json
import re
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.database import get_db
from app.auth.deps import require_user
from app.schemas.composition import (
    Composition,
    CompositionOut,
    CompositionStep,
    TransformRule,
)

logger = logging.getLogger("komajdon")
router = APIRouter(prefix="/api/compositions", tags=["compositions"])
_registry: dict[str, Composition] = {}


@router.get("/")
async def list_compositions(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    docs = await db["_compositions"].find().to_list(1000)
    return [
        CompositionOut(
            _id=str(d["_id"]),
            name=d["name"],
            description=d.get("description", ""),
            method=d.get("method", "GET"),
            steps=d.get("steps", []),
            output_step=d.get("output_step", ""),
            created_at=d.get("created_at", ""),
        )
        for d in docs
    ]


@router.post("/")
async def create_composition(
    body: Composition,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    existing = await db["_compositions"].find_one({"name": body.name})
    if existing:
        raise HTTPException(status_code=409, detail=f"Composition '{body.name}' already exists")

    doc = {
        "name": body.name,
        "description": body.description,
        "method": body.method.upper(),
        "steps": [s.model_dump() for s in body.steps],
        "output_step": body.output_step,
        "created_at": body.name,
    }
    result = await db["_compositions"].insert_one(doc)

    comp = Composition(**{k: v for k, v in doc.items() if k != "_id"})
    await _register_composition_route(comp, request.app)

    return {
        "message": f"Composition '{body.name}' created at /api/composed/{body.name}",
        "id": str(result.inserted_id),
    }


@router.put("/{name}")
async def update_composition(
    name: str,
    body: Composition,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    existing = await db["_compositions"].find_one({"name": name})
    if not existing:
        raise HTTPException(status_code=404, detail="Composition not found")

    updated_doc = {
        "name": body.name,
        "description": body.description,
        "method": body.method.upper(),
        "steps": [s.model_dump() for s in body.steps],
        "output_step": body.output_step,
        "created_at": existing.get("created_at", body.name),
    }
    await db["_compositions"].replace_one({"name": name}, updated_doc)

    _registry.pop(name, None)
    comp = Composition(**{k: v for k, v in updated_doc.items() if k != "_id"})
    await _register_composition_route(comp, request.app)

    return {"message": f"Composition '{name}' updated"}


@router.delete("/{name}")
async def delete_composition(
    name: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_user),
):
    result = await db["_compositions"].delete_one({"name": name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Composition not found")
    _registry.pop(name, None)
    return {"message": f"Composition '{name}' deleted"}


def _interpolate(template: str, context: dict[str, Any]) -> str:
    def _replace(m: re.Match) -> str:
        expr = m.group(1).strip()
        parts = expr.split(".")
        val: Any = context
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p, f"{{{{{expr}}}}}")
            elif isinstance(val, list) and p.isdigit():
                idx = int(p)
                val = val[idx] if 0 <= idx < len(val) else f"{{{{{expr}}}}}"
            else:
                return f"{{{{{expr}}}}}"
        return str(val) if not isinstance(val, (dict, list)) else json.dumps(val)

    return re.sub(r"\{\{(.+?)\}\}", _replace, template)


def _apply_transform(data: Any, rules: list[TransformRule]) -> Any:
    for rule in rules:
        op = rule.op
        p = rule.params
        if op == "pick" and isinstance(data, list):
            keys = p.get("keys", [])
            data = [{k: item.get(k) for k in keys if k in item} for item in data]
        elif op == "omit" and isinstance(data, list):
            keys = set(p.get("keys", []))
            data = [{k: v for k, v in item.items() if k not in keys} for item in data]
        elif op == "rename" and isinstance(data, list):
            mapping = p.get("mapping", {})
            for item in data:
                for old, new in mapping.items():
                    if old in item:
                        item[new] = item.pop(old)
        elif op == "compute" and isinstance(data, list):
            expr = p.get("expr", "")
            target = p.get("target", "")
            for item in data:
                try:
                    ctx = dict(item)
                    if "len" in expr:
                        field = expr.split("len(")[1].rstrip(")")
                        item[target] = len(ctx.get(field, ""))
                    elif "+" in expr and ":" not in expr:
                        left, right = expr.split("+")
                        item[target] = str(ctx.get(left.strip(), "")) + str(ctx.get(right.strip(), ""))
                except Exception:
                    logger.warning("Compute transform failed for target '%s'", target)
                    item[target] = None
        elif op == "filter" and isinstance(data, list):
            field = p.get("field", "")
            operator = p.get("operator", "eq")
            value = p.get("value")
            data = [item for item in data if _compare(item.get(field), operator, value)]
        elif op == "sort" and isinstance(data, list):
            field = p.get("field", "")
            desc = p.get("desc", False)
            data.sort(key=lambda x: x.get(field) or "", reverse=desc)
    return data


def _compare(val: Any, op: str, target: Any) -> bool:
    if op == "eq":
        return val == target
    elif op == "ne":
        return val != target
    elif op == "gt":
        try:
            return float(val) > float(target)
        except (TypeError, ValueError):
            return False
    elif op == "lt":
        try:
            return float(val) < float(target)
        except (TypeError, ValueError):
            return False
    elif op == "contains":
        return target in str(val)
    elif op == "exists":
        return val is not None
    return True


async def _execute_step(
    step: CompositionStep,
    context: dict[str, Any],
    base_url: str,
    auth_token: str | None,
) -> Any:
    if step.type == "request":
        path = _interpolate(step.path, context)
        if path.startswith("http://") or path.startswith("https://"):
            raise HTTPException(status_code=400, detail="External URLs not allowed in composition steps")
        if ".." in path:
            raise HTTPException(status_code=400, detail="Path traversal not allowed in composition steps")
        if not path.startswith("/api/"):
            raise HTTPException(status_code=400, detail="Only /api/* paths allowed in composition steps")
        url = f"{base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        body = _interpolate(json.dumps(step.body), context) if step.body else None
        body_parsed = json.loads(body) if body else None

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=step.method,
                url=url,
                headers={**headers, **step.headers},
                json=body_parsed,
            )
            try:
                return resp.json()
            except Exception:
                return resp.text

    elif step.type == "transform":
        source_data = None
        for sid in step.source_steps:
            if sid in context:
                source_data = context[sid]
                break
        if source_data is None:
            raise HTTPException(status_code=422, detail=f"Transform step '{step.id}': source step not found")
        return _apply_transform(source_data, step.transform_rules)

    elif step.type == "merge":
        sources = []
        for sid in step.source_steps:
            if sid in context:
                sources.append(context[sid])
        if step.merge_mode == "object":
            result = {}
            for sid in step.source_steps:
                val = context.get(sid)
                if isinstance(val, dict):
                    result.update(val)
                elif isinstance(val, list):
                    result[sid] = val
            return result
        elif step.merge_mode == "zip":
            if len(sources) < 2:
                return sources[0] if sources else []
            min_len = min(len(s) for s in sources if isinstance(s, list))
            result = []
            for i in range(min_len):
                merged = {}
                for s in sources:
                    if isinstance(s, list) and i < len(s) and isinstance(s[i], dict):
                        merged.update(s[i])
                result.append(merged)
            return result
        else:
            result = []
            for s in sources:
                if isinstance(s, list):
                    result.extend(s)
                elif isinstance(s, dict):
                    result.append(s)
            return result

    return None


async def run_composition(
    comp: Composition,
    request: Request,
    db: AsyncIOMotorDatabase,
    user: dict | None,
) -> Any:
    base_url = str(request.base_url).rstrip("/")
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    auth_token = token or None

    context: dict[str, Any] = {}

    for step in comp.steps:
        try:
            result = await _execute_step(step, context, base_url, auth_token)
            context[step.id] = result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Step '{step.id}' ({step.type}) failed: {e}",
            )

    if comp.output_step:
        return context.get(comp.output_step, context)
    return context


async def _register_composition_route(comp: Composition, app):
    _registry[comp.name] = comp

    async def endpoint(
        req: Request,
        db: AsyncIOMotorDatabase = Depends(get_db),
        user: dict | None = Depends(require_user),
    ):
        return await run_composition(comp, req, db, user)

    app.add_api_route(
        f"/api/composed/{comp.name}",
        endpoint=endpoint,
        methods=[comp.method],
        summary=f"Composed API: {comp.name}",
        tags=["composed"],
    )


def get_registry() -> dict[str, Composition]:
    return dict(_registry)
