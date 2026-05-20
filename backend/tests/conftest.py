from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.config import settings


# ── Patch config before app starts ───────────────────
settings.secret_key = "test-secret-key-12345"
settings.mongodb_url = "mongodb://fake:27017"
settings.cors_origins = ["*"]
settings.password_min_length = 4
settings.rate_limit_max = 1000
settings.rate_limit_auth_max = 1000


# ── Mock database ───────────────────────────────────
class MockCollection:
    """In-memory MongoDB collection mock."""

    def __init__(self):
        self._docs: dict[str, dict] = {}
        self._counter = 0

    async def _next_id(self):
        self._counter += 1
        return f"abc{self._counter:024d}"

    async def find_one(self, query, projection=None, **kwargs):
        for doc in self._docs.values():
            if all(doc.get(k) == v for k, v in query.items() if k.startswith("$") is False):
                if isinstance(projection, dict) and "_id" in projection:
                    return {k: v for k, v in doc.items() if k in projection or k == "_id"}
                return dict(doc)
        return None

    async def find(self, query=None, projection=None, **kwargs):
        return MockCursor(list(self._docs.values()), query, projection)

    async def insert_one(self, doc):
        doc = dict(doc)
        doc["_id"] = await self._next_id()
        self._docs[str(doc["_id"])] = doc
        return MagicMock(inserted_id=doc["_id"])

    async def insert_many(self, docs):
        ids = []
        for doc in docs:
            result = await self.insert_one(doc)
            ids.append(result.inserted_id)
        return MagicMock(inserted_ids=ids)

    async def update_one(self, query, update, **kwargs):
        doc_id = query.get("_id")
        if doc_id and doc_id in self._docs:
            self._apply_update(self._docs[str(doc_id)], update)
            return MagicMock(matched_count=1, modified_count=1)
        for doc in list(self._docs.values()):
            if all(doc.get(k) == v for k, v in query.items() if k.startswith("$") is False):
                self._apply_update(doc, update)
                return MagicMock(matched_count=1, modified_count=1)
        return MagicMock(matched_count=0, modified_count=0)

    def _apply_update(self, doc, update):
        if "$set" in update:
            doc.update(update["$set"])
        if "$inc" in update:
            for key, val in update["$inc"].items():
                doc[key] = doc.get(key, 0) + val

    async def update_many(self, query, update):
        count = 0
        for doc in list(self._docs.values()):
            if all(doc.get(k) == v for k, v in query.items() if k.startswith("$") is False):
                if "$set" in update:
                    doc.update(update["$set"])
                count += 1
        return MagicMock(matched_count=count, modified_count=count)

    async def delete_one(self, query):
        doc_id = query.get("_id")
        if doc_id and doc_id in self._docs:
            del self._docs[str(doc_id)]
            return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)

    async def delete_many(self, query):
        ids = list(self._docs.keys())
        count = 0
        for did in ids:
            doc = self._docs[did]
            if all(doc.get(k) == v for k, v in query.items() if k.startswith("$") is False):
                del self._docs[did]
                count += 1
        return MagicMock(deleted_count=count)

    async def create_index(self, *args, **kwargs):
        pass

    async def drop(self):
        self._docs.clear()

    def aggregate(self, pipeline):
        return MockCursor(list(self._docs.values()), None, None)


class MockCursor:
    def __init__(self, docs, query=None, projection=None):
        self._docs = list(docs)
        self._skip_val = 0
        self._limit_val = 1000
        self._sort_spec = None

    def skip(self, n):
        self._skip_val = n
        return self

    def limit(self, n):
        self._limit_val = n
        return self

    def sort(self, *args, **kwargs):
        return self

    async def to_list(self, length):
        start = self._skip_val
        end = start + min(length, self._limit_val)
        return self._docs[start:end]


@pytest.fixture
def mock_db():
    """Returns a dict of collection_name -> MockCollection."""
    collections = {}

    def get_collection(name):
        if name not in collections:
            collections[name] = MockCollection()
        return collections[name]

    return get_collection


@pytest_asyncio.fixture
async def client(mock_db) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with mocked MongoDB."""
    from app.database import get_db

    async def override_get_db():
        return mock_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client, mock_db):
    """Register + promote an admin user, return token."""
    from app.auth.jwt import hash_password
    users = mock_db("users")
    roles = mock_db("_roles")
    await users.insert_one({
        "email": "admin@test.com",
        "password": hash_password("Admin1234!"),
        "role": "admin",
        "permissions": [],
        "email_verified": True,
        "is_active": True,
        "created_at": "now",
    })
    await roles.insert_one({
        "name": "admin",
        "description": "Admin",
        "permissions": [
            "api:access", "users:read", "users:create", "users:update", "users:delete",
            "models:read", "models:create", "models:update", "models:delete",
            "roles:read", "roles:create", "roles:update", "roles:delete",
            "system:health", "system:logs", "system:settings",
        ],
        "is_default": False,
        "created_at": "now",
    })
    r = await client.post("/api/auth/signin", json={"email": "admin@test.com", "password": "Admin1234!"})
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client, mock_db):
    """Register a regular user, return token."""
    from app.auth.jwt import hash_password
    users = mock_db("users")
    roles = mock_db("_roles")
    await users.insert_one({
        "email": "user@test.com",
        "password": hash_password("User1234!"),
        "role": "user",
        "permissions": ["api:access", "*:read", "system:health"],
        "email_verified": False,
        "is_active": True,
        "created_at": "now",
    })
    await roles.insert_one({
        "name": "user",
        "description": "Default user",
        "permissions": ["api:access", "*:read", "system:health"],
        "is_default": True,
        "created_at": "now",
    })
    r = await client.post("/api/auth/signin", json={"email": "user@test.com", "password": "User1234!"})
    return r.json()["access_token"]
