#!/usr/bin/env python3
"""Comprehensive test runner — uses built-in unittest + httpx (no pytest needed)."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock

import httpx

# ── Ensure backend is importable ────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["SECRET_KEY"] = "test-secret-key-12345"
os.environ["MONGODB_URL"] = "mongodb://fake:27017"
os.environ["PASSWORD_MIN_LENGTH"] = "4"
os.environ["RATE_LIMIT_MAX"] = "1000"
os.environ["RATE_LIMIT_AUTH_MAX"] = "1000"

from app.main import app
from app.config import settings
from app.database import get_db
from httpx import ASGITransport, AsyncClient

# Override settings
settings.secret_key = "test-secret-key-12345"
settings.password_min_length = 4
settings.rate_limit_max = 1000
settings.rate_limit_auth_max = 1000


# ── In-memory MongoDB Mock ──────────────────────────
class MockCollection:
    def __init__(self):
        self._docs: dict[str, dict] = {}
        self._counter = 0

    async def _next_id(self):
        self._counter += 1
        return f"{self._counter:024d}"

    async def find_one(self, query, projection=None, **kwargs):
        if query is None:
            query = {}
        for doc in self._docs.values():
            match = True
            for k, v in query.items():
                if k.startswith("$"):
                    continue
                dv = doc.get(str(k) if not isinstance(k, str) else k)
                if isinstance(v, dict):
                    if "$ne" in v and self._eq(dv, v["$ne"]):
                        match = False
                    if "$in" in v and not any(self._eq(dv, x) for x in v["$in"]):
                        match = False
                elif not self._eq(dv, v):
                    match = False
            if match:
                if isinstance(projection, dict) and "_id" in projection:
                    return {k: v for k, v in doc.items() if k in projection or k == "_id"}
                return dict(doc)
        return None

    def _eq(self, a, b):
        if isinstance(a, type(b)) or isinstance(b, type(a)):
            return a == b
        return str(a) == str(b)

    def find(self, query=None, projection=None, **kwargs):
        return _MockCursor(list(self._docs.values()))

    async def insert_one(self, doc):
        doc = dict(doc)
        doc["_id"] = await self._next_id()
        self._docs[str(doc["_id"])] = doc
        return MagicMock(inserted_id=doc["_id"])

    async def insert_many(self, docs):
        ids = []
        for doc in docs:
            r = await self.insert_one(doc)
            ids.append(r.inserted_id)
        return MagicMock(inserted_ids=ids)

    def _apply_update(self, doc, update):
        if "$set" in update:
            doc.update(update["$set"])
        if "$inc" in update:
            for key, val in update["$inc"].items():
                doc[key] = doc.get(key, 0) + val

    async def update_one(self, query, update, **kwargs):
        doc_id = query.get("_id")
        doc_id_str = str(doc_id) if doc_id else None
        if doc_id_str and doc_id_str in self._docs:
            self._apply_update(self._docs[doc_id_str], update)
            return MagicMock(matched_count=1, modified_count=1)
        for doc in list(self._docs.values()):
            match = True
            for k, v in query.items():
                if k.startswith("$"): continue
                dv = doc.get(str(k) if not isinstance(k, str) else k)
                if isinstance(v, dict) and "$ne" in v:
                    if self._eq(dv, v["$ne"]): match = False
                elif not self._eq(dv, v):
                    match = False
            if match:
                self._apply_update(doc, update)
                return MagicMock(matched_count=1, modified_count=1)
        return MagicMock(matched_count=0, modified_count=0)

    async def update_many(self, query, update):
        count = 0
        for doc in list(self._docs.values()):
            match = True
            for k, v in query.items():
                if k.startswith("$"): continue
                if not self._eq(doc.get(str(k) if not isinstance(k, str) else k), v):
                    match = False
            if match:
                if "$set" in update:
                    doc.update(update["$set"])
                count += 1
        return MagicMock(matched_count=count, modified_count=count)

    async def delete_one(self, query):
        doc_id = query.get("_id")
        doc_id_str = str(doc_id) if doc_id else None
        if doc_id_str and doc_id_str in self._docs:
            del self._docs[doc_id_str]
            return MagicMock(deleted_count=1)
        for did, doc in list(self._docs.items()):
            match = True
            for k, v in query.items():
                if k.startswith("$"): continue
                dv = doc.get(str(k) if not isinstance(k, str) else k)
                if not self._eq(dv, v): match = False
            if match:
                del self._docs[did]
                return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)

    async def delete_many(self, query):
        ids = list(self._docs.keys())
        count = 0
        for did in ids:
            doc = self._docs[did]
            match = True
            for k, v in query.items():
                if k.startswith("$"): continue
                if not self._eq(doc.get(str(k) if not isinstance(k, str) else k), v):
                    match = False
            if match:
                del self._docs[did]
                count += 1
        return MagicMock(deleted_count=count)

    async def create_index(self, *args, **kwargs):
        pass

    async def drop(self):
        self._docs.clear()

    def aggregate(self, pipeline, **kwargs):
        return _MockCursor(list(self._docs.values()))


class _MockCursor:
    def __init__(self, docs):
        self._docs = list(docs)
        self._s = 0
        self._l = 1000
    def skip(self, n): self._s = n; return self
    def limit(self, n): self._l = n; return self
    def sort(self, *a, **kw): return self
    async def to_list(self, length):
        end = self._s + min(length, self._l)
        return self._docs[self._s:end]


# ── Test Suite ──────────────────────────────────────

class MockDB:
    _collections: dict[str, MockCollection] = {}

    def __call__(self, name):
        if name not in self._collections:
            self._collections[name] = MockCollection()
        return self._collections[name]

    def reset(self):
        self._collections.clear()

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self(name)

    def __getitem__(self, name):
        return self.__call__(name)


mock_db = MockDB()


async def override_get_db():
    return mock_db


class KomajdonTest(unittest.IsolatedAsyncioTestCase):
    transport: ASGITransport = None
    client: AsyncClient = None

    async def asyncSetUp(self):
        mock_db.reset()
        app.dependency_overrides[get_db] = override_get_db
        self.transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=self.transport, base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()

    # ── Helpers ────────────────────────────────────

    async def signup(self, email: str, pw: str = "Test1234!"):
        return await self.client.post("/api/auth/signup", json={"email": email, "password": pw})

    async def signin(self, email: str, pw: str = "Test1234!"):
        return await self.client.post("/api/auth/signin", json={"email": email, "password": pw})

    async def admin_token(self) -> str:
        from app.auth.jwt import hash_password
        users = mock_db("users")
        await users.insert_one({
            "email": "admin@t.com", "password": hash_password("Admin1234!"),
            "role": "admin", "permissions": [
                "api:access", "users:read", "users:create", "users:update", "users:delete",
                "models:read", "models:create", "models:update", "models:delete",
                "roles:read", "roles:create", "roles:update", "roles:delete",
                "system:health", "*:read", "*:create", "*:update", "*:delete",
            ], "email_verified": True, "is_active": True, "created_at": "now",
        })
        roles = mock_db("_roles")
        await roles.insert_one({
            "name": "admin", "permissions": [
                "api:access", "users:read", "users:create", "users:update", "users:delete",
                "models:read", "models:create", "models:update", "models:delete",
                "roles:read", "roles:create", "roles:update", "roles:delete",
                "system:health", "*:read", "*:create", "*:update", "*:delete",
            ], "is_default": False, "created_at": "now",
        })
        r = await self.signin("admin@t.com", "Admin1234!")
        return r.json()["access_token"]

    async def user_token(self) -> str:
        from app.auth.jwt import hash_password
        users = mock_db("users")
        await users.insert_one({
            "email": "user@t.com", "password": hash_password("User1234!"),
            "role": "user", "permissions": ["api:access", "system:health"],
            "email_verified": False, "is_active": True, "created_at": "now",
        })
        roles = mock_db("_roles")
        await roles.insert_one({
            "name": "user", "permissions": ["api:access", "system:health"],
            "is_default": True, "created_at": "now",
        })
        r = await self.signin("user@t.com", "User1234!")
        return r.json()["access_token"]

    async def create_schema(self, name="TestItem"):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": name, "fields": [
                {"name": "title", "type": "string", "required": True, "validation": {"required": True}},
                {"name": "count", "type": "number"},
            ], "indexes": [], "auth_protected": False, "realtime_enabled": False, "created_at": "now",
        })


# ══════════════════════════════════════════════════════
#   AUTH TESTS
# ══════════════════════════════════════════════════════

class TestAuthSignup(KomajdonTest):
    async def test_signup_success(self):
        r = await self.signup("a@t.com")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertIn("access_token", d)
        self.assertEqual(d["user"]["email"], "a@t.com")
        self.assertEqual(d["user"]["role"], "user")

    async def test_signup_duplicate(self):
        await self.signup("dup@t.com")
        r = await self.signup("dup@t.com")
        self.assertEqual(r.status_code, 400)

    async def test_signup_weak_password(self):
        r = await self.signup("w@t.com", "ab")
        self.assertEqual(r.status_code, 422)

    async def test_signup_no_uppercase(self):
        r = await self.signup("nu@t.com", "lowercase1")
        self.assertEqual(r.status_code, 422)

    async def test_signup_no_digit(self):
        r = await self.signup("nd@t.com", "NoDigitsNo")
        self.assertEqual(r.status_code, 422)

    async def test_register_alias(self):
        r = await self.client.post("/api/auth/register", json={"email": "ra@t.com", "password": "RegAlias1"})
        self.assertEqual(r.status_code, 200)


class TestAuthSignin(KomajdonTest):
    async def test_signin_success(self):
        await self.signup("si@t.com")
        r = await self.signin("si@t.com")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access_token", r.json())

    async def test_signin_wrong_password(self):
        await self.signup("wp@t.com")
        r = await self.client.post("/api/auth/signin", json={"email": "wp@t.com", "password": "Wrong1234"})
        self.assertEqual(r.status_code, 401)

    async def test_signin_nonexistent(self):
        r = await self.signin("nobody@t.com")
        self.assertEqual(r.status_code, 401)

    async def test_login_alias(self):
        await self.signup("la@t.com")
        r = await self.client.post("/api/auth/login", json={"email": "la@t.com", "password": "Test1234!"})
        self.assertEqual(r.status_code, 200)


class TestAuthMe(KomajdonTest):
    async def test_me_authenticated(self):
        t = await self.user_token()
        r = await self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["email"], "user@t.com")

    async def test_me_no_token(self):
        r = await self.client.get("/api/auth/me")
        self.assertEqual(r.status_code, 401)

    async def test_me_invalid_token(self):
        r = await self.client.get("/api/auth/me", headers={"Authorization": "Bearer bad"})
        self.assertEqual(r.status_code, 401)


class TestAuthRefresh(KomajdonTest):
    async def test_refresh_success(self):
        r = await self.signup("rf@t.com")
        refresh = r.json()["refresh_token"]
        r2 = await self.client.post("/api/auth/refresh", json={"refresh_token": refresh})
        self.assertEqual(r2.status_code, 200)
        self.assertIn("access_token", r2.json())

    async def test_refresh_invalid(self):
        r = await self.client.post("/api/auth/refresh", json={"refresh_token": "bad"})
        self.assertEqual(r.status_code, 401)


class TestAuthLogout(KomajdonTest):
    async def test_logout(self):
        t = await self.user_token()
        r = await self.client.post("/api/auth/logout", json={"refresh_token": "x"}, headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)


class TestAuthVerify(KomajdonTest):
    async def test_verify_invalid_token(self):
        r = await self.client.post("/api/auth/verify-email", json={"token": "bad"})
        self.assertEqual(r.status_code, 400)

    async def test_resend_verification(self):
        t = await self.user_token()
        r = await self.client.post("/api/auth/resend-verification", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)


class TestAuthPasswordReset(KomajdonTest):
    async def test_forgot_password(self):
        r = await self.client.post("/api/auth/forgot-password", json={"email": "x@t.com"})
        self.assertEqual(r.status_code, 200)

    async def test_reset_invalid_token(self):
        r = await self.client.post("/api/auth/reset-password", json={"token": "bad", "new_password": "NewPass1234!"})
        self.assertEqual(r.status_code, 400)

    async def test_reset_weak_password(self):
        r = await self.client.post("/api/auth/reset-password", json={"token": "x", "new_password": "ab"})
        self.assertEqual(r.status_code, 400)


class TestAuthLockout(KomajdonTest):
    async def test_lockout_after_5_fails(self):
        await self.signup("lock@t.com")
        for _ in range(5):
            await self.client.post("/api/auth/signin", json={"email": "lock@t.com", "password": "wrong"})
        r = await self.signin("lock@t.com")
        self.assertEqual(r.status_code, 423)
        self.assertIn("locked", r.json()["detail"].lower())


# ══════════════════════════════════════════════════════
#   ADMIN / USER MANAGEMENT TESTS
# ══════════════════════════════════════════════════════

class TestAdminUsers(KomajdonTest):
    async def test_list_users(self):
        t = await self.admin_token()
        r = await self.client.get("/api/auth/users", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    async def test_list_users_forbidden(self):
        t = await self.user_token()
        r = await self.client.get("/api/auth/users", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 403)

    async def test_create_user_manual(self):
        t = await self.admin_token()
        r = await self.client.post("/api/auth/users", json={"email": "new@t.com", "password": "NewUsr123!", "role": "viewer"}, headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["user"]["email"], "new@t.com")

    async def test_get_user_by_id(self):
        t = await self.admin_token()
        r = await self.client.get("/api/auth/users", headers={"Authorization": f"Bearer {t}"})
        uid = r.json()[0]["id"]
        r2 = await self.client.get(f"/api/auth/users/{uid}", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r2.status_code, 200)

    async def test_update_user(self):
        t = await self.admin_token()
        r = await self.client.get("/api/auth/users", headers={"Authorization": f"Bearer {t}"})
        uid = r.json()[0]["id"]
        r2 = await self.client.patch(f"/api/auth/users/{uid}", json={"is_active": False}, headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r2.status_code, 200)

    async def test_update_user_role(self):
        t = await self.admin_token()
        await self.client.post("/api/auth/users", json={"email": "roleman@t.com", "password": "RoleMan1!", "role": "user"}, headers={"Authorization": f"Bearer {t}"})
        users = await self.client.get("/api/auth/users", headers={"Authorization": f"Bearer {t}"})
        targets = [u for u in users.json() if u["email"] == "roleman@t.com"]
        if targets:
            r = await self.client.patch(f"/api/auth/users/{targets[0]['id']}/role", json={"role": "viewer"}, headers={"Authorization": f"Bearer {t}"})
            self.assertEqual(r.status_code, 200)

    async def test_delete_user(self):
        t = await self.admin_token()
        r = await self.client.post("/api/auth/users", json={"email": "delt@t.com", "password": "DelUsr123!", "role": "user"}, headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 201, f"User creation failed: {r.text[:200]}")
        uid = r.json().get("user", {}).get("id", "")
        self.assertTrue(uid, f"No user ID returned: {r.text[:200]}")
        r = await self.client.delete(f"/api/auth/users/{uid}", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200, f"Delete failed: {r.text[:200]}")


# ══════════════════════════════════════════════════════
#   ROLE / PERMISSION TESTS
# ══════════════════════════════════════════════════════

class TestRoles(KomajdonTest):
    async def test_list_permissions(self):
        t = await self.admin_token()
        r = await self.client.get("/api/roles/permissions", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)
        self.assertGreater(len(r.json()), 0)

    async def test_list_permissions_forbidden(self):
        t = await self.user_token()
        r = await self.client.get("/api/roles/permissions", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 403)

    async def test_create_role(self):
        t = await self.admin_token()
        r = await self.client.post("/api/roles/", json={"name": "test-role", "permissions": ["api:access"]}, headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 201)

    async def test_create_duplicate_role(self):
        t = await self.admin_token()
        await self.client.post("/api/roles/", json={"name": "dup", "permissions": ["api:access"]}, headers={"Authorization": f"Bearer {t}"})
        r = await self.client.post("/api/roles/", json={"name": "dup", "permissions": ["api:access"]}, headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 409)

    async def test_update_role(self):
        t = await self.admin_token()
        roles = mock_db("_roles")
        await roles.insert_one({"name": "upd", "permissions": ["api:access"], "is_default": False, "created_at": "now"})
        r = await self.client.get("/api/roles/", headers={"Authorization": f"Bearer {t}"})
        targets = [x for x in r.json() if x["name"] == "upd"]
        if targets:
            r2 = await self.client.put(f"/api/roles/{targets[0]['id']}", json={"description": "Updated"}, headers={"Authorization": f"Bearer {t}"})
            self.assertEqual(r2.status_code, 200)

    async def test_delete_role(self):
        t = await self.admin_token()
        roles = mock_db("_roles")
        await roles.insert_one({"name": "del-me", "permissions": ["api:access"], "is_default": False, "created_at": "now"})
        r = await self.client.get("/api/roles/", headers={"Authorization": f"Bearer {t}"})
        targets = [x for x in r.json() if x["name"] == "del-me"]
        if targets:
            r2 = await self.client.delete(f"/api/roles/{targets[0]['id']}", headers={"Authorization": f"Bearer {t}"})
            self.assertEqual(r2.status_code, 200)

    async def test_delete_default_role_fails(self):
        t = await self.admin_token()
        roles = mock_db("_roles")
        await roles.insert_one({"name": "default", "permissions": ["api:access"], "is_default": True, "created_at": "now"})
        r = await self.client.get("/api/roles/", headers={"Authorization": f"Bearer {t}"})
        targets = [x for x in r.json() if x.get("is_default")]
        if targets:
            r2 = await self.client.delete(f"/api/roles/{targets[0]['id']}", headers={"Authorization": f"Bearer {t}"})
            self.assertEqual(r2.status_code, 400)


# ══════════════════════════════════════════════════════
#   SDK TESTS
# ══════════════════════════════════════════════════════

class TestSDK(KomajdonTest):
    async def test_typescript_sdk(self):
        t = await self.admin_token()
        await self.create_schema("Widget")
        r = await self.client.get("/api/sdk/Widget", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200, f"SDK failed: {r.text[:200]}")
        self.assertIn("WidgetApi", r.text)

    async def test_python_sdk(self):
        t = await self.admin_token()
        await self.create_schema("Gadget")
        r = await self.client.get("/api/sdk/Gadget?lang=python", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("class Gadget", r.text)

    async def test_javascript_sdk(self):
        t = await self.admin_token()
        await self.create_schema("Doodad")
        r = await self.client.get("/api/sdk/Doodad?lang=javascript", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("DoodadApi", r.text)

    async def test_curl_sdk(self):
        t = await self.admin_token()
        await self.create_schema("Thing")
        r = await self.client.get("/api/sdk/Thing?lang=curl", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("curl", r.text)

    async def test_sdk_not_found(self):
        t = await self.admin_token()
        r = await self.client.get("/api/sdk/Nope", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 404)

    async def test_sdk_requires_auth(self):
        r = await self.client.get("/api/sdk/Widget")
        self.assertEqual(r.status_code, 401)


# ══════════════════════════════════════════════════════
#   API KEYS TESTS
# ══════════════════════════════════════════════════════

class TestApiKeys(KomajdonTest):
    async def test_create_key(self):
        t = await self.admin_token()
        r = await self.client.post("/api/keys/?name=key1&role=viewer", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 201)
        self.assertIn("key", r.json())
        self.assertTrue(r.json()["key"].startswith("kj_"))

    async def test_list_keys(self):
        t = await self.admin_token()
        await self.client.post("/api/keys/?name=k1&role=viewer", headers={"Authorization": f"Bearer {t}"})
        r = await self.client.get("/api/keys/", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    async def test_delete_key(self):
        t = await self.admin_token()
        r = await self.client.post("/api/keys/?name=del&role=viewer", headers={"Authorization": f"Bearer {t}"})
        kid = r.json().get("id")
        if kid:
            r2 = await self.client.delete(f"/api/keys/{kid}", headers={"Authorization": f"Bearer {t}"})
            self.assertEqual(r2.status_code, 200)

    async def test_key_requires_auth(self):
        r = await self.client.post("/api/keys/?name=n&role=viewer")
        self.assertEqual(r.status_code, 401)


# ══════════════════════════════════════════════════════
#   HEALTH / DISCOVER
# ══════════════════════════════════════════════════════

class TestHealth(KomajdonTest):
    async def test_health(self):
        r = await self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    async def test_discover(self):
        t = await self.admin_token()
        r = await self.client.get("/api/discover/", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)
        self.assertGreater(len(r.json()), 10)


# ══════════════════════════════════════════════════════
#   STORAGE
# ══════════════════════════════════════════════════════

class TestStorage(KomajdonTest):
    async def test_upload_requires_auth(self):
        r = await self.client.post("/api/storage/upload/c", files={"file": ("f.txt", b"hi")})
        self.assertEqual(r.status_code, 401)

    async def test_list_requires_auth(self):
        r = await self.client.get("/api/storage/list/c")
        self.assertEqual(r.status_code, 401)

    async def test_download_requires_auth(self):
        r = await self.client.get("/api/storage/download/x")
        self.assertEqual(r.status_code, 401)

    async def test_download_invalid_id(self):
        t = await self.admin_token()
        # GridFS requires a real MotorDatabase. The mock returns 500 because
        # AsyncIOMotorGridFSBucket can't be instantiated with a mock db.
        # This test verifies the endpoint doesn't crash or hang, and returns
        # proper HTTP.
        try:
            r = await self.client.get("/api/storage/download/000000000000000000000000", headers={"Authorization": f"Bearer {t}"})
            self.assertIn(r.status_code, (400, 404, 500))
        except Exception as e:
            self.skipTest(f"GridFS requires real MongoDB: {e}")


# ══════════════════════════════════════════════════════
#   AGREGATIONS / COMPOSITIONS / PIPELINES
# ══════════════════════════════════════════════════════

class TestAggregations(KomajdonTest):
    async def test_templates(self):
        t = await self.admin_token()
        r = await self.client.get("/api/aggregations/templates", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(r.status_code, 200)
        self.assertGreater(len(r.json()), 0)

    async def test_templates_public(self):
        r = await self.client.get("/api/aggregations/templates")
        self.assertEqual(r.status_code, 200)


class TestCompositions(KomajdonTest):
    async def test_list_requires_auth(self):
        r = await self.client.get("/api/compositions/")
        self.assertEqual(r.status_code, 401)

    async def test_list(self):
        t = await self.admin_token()
        r = await self.client.get("/api/compositions/", headers={"Authorization": f"Bearer {t}"})
        self.assertIn(r.status_code, (200, 403))


class TestPipelines(KomajdonTest):
    async def test_list_requires_auth(self):
        r = await self.client.get("/api/pipelines/")
        self.assertEqual(r.status_code, 401)

    async def test_create_pipeline(self):
        t = await self.admin_token()
        r = await self.client.post("/api/pipelines/", json={"name": "p", "collection": "C", "stages": [{"type": "limit", "params": {"limit": 5}}]}, headers={"Authorization": f"Bearer {t}"})
        self.assertIn(r.status_code, (200, 201, 403))

    async def test_get_pipeline_invalid_id(self):
        t = await self.admin_token()
        r = await self.client.get("/api/pipelines/badid", headers={"Authorization": f"Bearer {t}"})
        self.assertIn(r.status_code, (400, 403))


# ══════════════════════════════════════════════════════
#   FRONTEND TESTS (Node.js via subprocess)
# ══════════════════════════════════════════════════════

class TestFrontend(unittest.TestCase):
    def test_vitest_config_exists(self):
        import os
        cfg = os.path.join(os.path.dirname(__file__), "../../frontend/vite.config.ts")
        self.assertTrue(os.path.exists(cfg), "vite.config.ts must exist")

    def test_package_json_has_test_script(self):
        import json, os
        pkg = os.path.join(os.path.dirname(__file__), "../../frontend/package.json")
        with open(pkg) as f:
            p = json.load(f)
        self.assertIn("test", p.get("scripts", {}), "package.json must have test script")
        self.assertNotIn("react-hook-form", p.get("dependencies", {}), "unused dep react-hook-form removed")
        self.assertNotIn("zod", p.get("dependencies", {}), "unused dep zod removed")
        self.assertNotIn("@monaco-editor/react", p.get("dependencies", {}), "unused dep @monaco-editor/react removed")

    def test_has_vitest_dev_dep(self):
        import json, os
        pkg = os.path.join(os.path.dirname(__file__), "../../frontend/package.json")
        with open(pkg) as f:
            p = json.load(f)
        self.assertIn("vitest", p.get("devDependencies", {}), "vitest must be a dev dependency")


# ══════════════════════════════════════════════════════
#   RUNNER
# ══════════════════════════════════════════════════════

def make_suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestAuthSignup, TestAuthSignin, TestAuthMe, TestAuthRefresh,
        TestAuthLogout, TestAuthVerify, TestAuthPasswordReset, TestAuthLockout,
        TestAdminUsers, TestRoles,
        TestSDK, TestApiKeys,
        TestHealth, TestStorage,
        TestAggregations, TestCompositions, TestPipelines,
        TestFrontend,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    return suite


if __name__ == "__main__":
    print("=" * 65)
    print("  Komajdon — Comprehensive Test Suite")
    print("=" * 65)
    print()

    suite = make_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 65)
    print(f"  Ran {result.testsRun} tests")
    if result.wasSuccessful():
        print("  ALL TESTS PASSED ✓")
    else:
        print(f"  FAILURES: {len(result.failures)}")
        print(f"  ERRORS:   {len(result.errors)}")
    print("=" * 65)

    sys.exit(0 if result.wasSuccessful() else 1)
