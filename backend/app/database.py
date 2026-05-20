from __future__ import annotations

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

logger = logging.getLogger("komajdon")
client: AsyncIOMotorClient | None = None


def _get_tls_kwargs() -> dict:
    url = settings.mongodb_url
    if url.startswith("mongodb+srv://"):
        return {"tls": True}
    return {}


async def get_db():
    if client is None:
        raise RuntimeError("Database not initialized")
    return client[settings.database_name]


async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.mongodb_url, **_get_tls_kwargs())
    db = client[settings.database_name]
    await db.users.create_index("email", unique=True)
    await db["_schemas"].create_index([("name", 1), ("project_id", 1)], unique=True)
    await db["_refresh_tokens"].create_index("token", unique=True)
    await db["_refresh_tokens"].create_index("email")
    await db["_refresh_tokens"].create_index("created_at", expireAfterSeconds=settings.refresh_token_expire_minutes * 60)
    await db["_roles"].create_index("name", unique=True)
    await db["_api_keys"].create_index("key", unique=True)
    await db["_api_keys"].create_index("user_id")
    await db["_projects"].create_index("slug", unique=True)
    logger.info("Connected to MongoDB at %s (db=%s)", settings.mongodb_url, settings.database_name)
    return db


async def close_db():
    global client
    if client:
        client.close()
        client = None
