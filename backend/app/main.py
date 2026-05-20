from __future__ import annotations

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import connect_db, close_db
from app.exceptions import global_exception_handler
from app.middleware import RateLimitMiddleware, AuditLogMiddleware, SecurityHeadersMiddleware
from app.routes import auth, models, aggregations, files, pipelines, realtime, sdk, compositions, discover, roles, api_keys, projects, rate_limits
from app.routes.dynamic import router as dynamic_router, generate_routes_for_schema
from app.routes.compositions import _register_composition_route
from app.routes.pipelines import _register_aggregation_route
from app.schemas.model_schema import ModelSchema
from app.schemas.composition import Composition
from app.routes.roles import _seed_default_roles
from app.middleware import reload_rate_limit_rules

logger = logging.getLogger("komajdon")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await connect_db()

    await _seed_default_roles(db)
    await reload_rate_limit_rules(db)

    schemas = await db["_schemas"].find().to_list(1000)
    for s in schemas:
        try:
            schema = ModelSchema(
                name=s["name"],
                fields=[f for f in s.get("fields", [])],
                indexes=s.get("indexes", []),
                auth_protected=s.get("auth_protected", False),
                realtime_enabled=s.get("realtime_enabled", False),
            )
            await generate_routes_for_schema(schema, app)
        except Exception as e:
            logger.warning("Could not regenerate routes for '%s': %s", s.get("name"), e)

    comps = await db["_compositions"].find().to_list(1000)
    for c in comps:
        try:
            comp = Composition(
                name=c["name"],
                description=c.get("description", ""),
                method=c.get("method", "GET"),
                steps=c.get("steps", []),
                output_step=c.get("output_step", ""),
            )
            await _register_composition_route(comp, app)
        except Exception as e:
            logger.warning("Could not restore composition '%s': %s", c.get("name"), e)

    pipelines = await db["_pipelines"].find({"expose_as_api": True}).to_list(1000)
    for p in pipelines:
        try:
            _register_aggregation_route(
                name=p["name"],
                collection=p["collection"],
                stages=p.get("stages", []),
                method=p.get("api_method", "GET"),
                app=app,
            )
        except Exception as e:
            logger.warning("Could not restore aggregation route '%s': %s", p.get("name"), e)

    yield
    await close_db()


app = FastAPI(
    title="Komajdon",
    description="Visual Backends for MongoDB — Just Point & Click",
    version="0.0.1",
    lifespan=lifespan,
)

app.add_exception_handler(Exception, global_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(AuditLogMiddleware)

app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_max,
    window_seconds=settings.rate_limit_window,
    auth_max=settings.rate_limit_auth_max,
)

app.include_router(auth.router)
app.include_router(models.router)
app.include_router(dynamic_router)
app.include_router(aggregations.router)
app.include_router(files.router)
app.include_router(pipelines.router)
app.include_router(realtime.router)
app.include_router(sdk.router)
app.include_router(compositions.router)
app.include_router(discover.router)
app.include_router(roles.router)
app.include_router(api_keys.router)
app.include_router(projects.router)
app.include_router(rate_limits.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def serve_admin():
    return FileResponse("app/static/admin.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "komajdon"}
