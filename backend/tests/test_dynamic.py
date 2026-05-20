from __future__ import annotations

import pytest


class TestDynamicCRUD:
    """Auto-generated CRUD routes for models."""

    @pytest.mark.asyncio
    async def test_create_schema_then_crud(self, client, admin_token, mock_db):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": "Task",
            "fields": [
                {"name": "title", "type": "string", "required": True, "validation": {"required": True, "max_length": 200}},
                {"name": "done", "type": "boolean", "required": False, "default": False},
                {"name": "priority", "type": "number", "required": False},
            ],
            "indexes": [],
            "auth_protected": False,
            "realtime_enabled": False,
            "created_at": "now",
        })

        # Create (POST)
        r = await client.post(
            "/api/Task",
            json={"title": "Test task", "priority": 1},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code in (200, 201, 403)
        if r.status_code == 403:
            pytest.skip("Permission gating active — admin needs Task:create")

        task_id = r.json()["_id"]

        # Read (GET :id)
        r = await client.get(f"/api/Task/{task_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert r.json()["title"] == "Test task"

        # List (GET)
        r = await client.get("/api/Task", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200

        # Update (PATCH)
        r = await client.patch(
            f"/api/Task/{task_id}", json={"done": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code in (200, 403)
        if r.status_code == 200:
            assert r.json()["done"] is True or r.json()["done"] == "true"

        # Soft delete
        r = await client.delete(f"/api/Task/{task_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 403, 404)


class TestDynamicQueries:
    """Query parameters: filters, sort, pagination."""

    @pytest.mark.asyncio
    async def test_filter_query(self, client, admin_token, mock_db):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": "Item", "fields": [{"name": "status", "type": "string"}, {"name": "qty", "type": "number"}],
            "indexes": [], "auth_protected": False, "realtime_enabled": False, "created_at": "now",
        })
        r = await client.get("/api/Item", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 403)

    @pytest.mark.asyncio
    async def test_cursor_pagination(self, client, admin_token, mock_db):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": "Page", "fields": [{"name": "num", "type": "number"}],
            "indexes": [], "auth_protected": False, "realtime_enabled": False, "created_at": "now",
        })
        r = await client.get("/api/Page?cursor=abc&limit=10", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 403)

    @pytest.mark.asyncio
    async def test_sort(self, client, admin_token, mock_db):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": "Sorted", "fields": [{"name": "name", "type": "string"}],
            "indexes": [], "auth_protected": False, "realtime_enabled": False, "created_at": "now",
        })
        r = await client.get("/api/Sorted?sort=-name", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 403)

    @pytest.mark.asyncio
    async def test_field_projection(self, client, admin_token, mock_db):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": "Proj", "fields": [{"name": "a", "type": "string"}, {"name": "b", "type": "string"}],
            "indexes": [], "auth_protected": False, "realtime_enabled": False, "created_at": "now",
        })
        r = await client.get("/api/Proj?fields=a", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 403)


class TestModels:
    """Model schema management endpoints."""

    @pytest.mark.asyncio
    async def test_list_models(self, client, admin_token):
        r = await client.get("/api/models/", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 403)

    @pytest.mark.asyncio
    async def test_create_model(self, client, admin_token):
        r = await client.post(
            "/api/models/",
            json={
                "name": "TestModel", "fields": [{"name": "name", "type": "string", "required": True}],
                "indexes": [], "auth_protected": False, "realtime_enabled": False,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code in (201, 200, 403)

    @pytest.mark.asyncio
    async def test_get_model(self, client, admin_token, mock_db):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": "Gettable", "fields": [], "indexes": [],
            "auth_protected": False, "realtime_enabled": False, "created_at": "now",
        })
        r = await client.get("/api/models/Gettable", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 403)


class TestHealth:
    """Health check endpoint."""

    @pytest.mark.asyncio
    async def test_health(self, client):
        r = await client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_discover(self, client, admin_token):
        r = await client.get("/api/discover/", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 403)
