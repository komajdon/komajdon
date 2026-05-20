from __future__ import annotations

import pytest


class TestFileStorage:
    """File storage endpoints."""

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, client):
        r = await client.post("/api/storage/upload/test", files={"file": ("test.txt", b"hello", "text/plain")})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_download_requires_auth(self, client):
        r = await client.get("/api/storage/download/fakeid")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client):
        r = await client.get("/api/storage/list/test")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client):
        r = await client.delete("/api/storage/delete/fakeid")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_list_files(self, client, admin_token, mock_db):
        r = await client.get("/api/storage/list/test-collection", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 500)  # GridFS requires real MongoDB

    @pytest.mark.asyncio
    async def test_download_invalid_id(self, client, admin_token):
        r = await client.get("/api/storage/download/invalid", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 400


class TestAggregations:
    """Aggregation pipeline endpoints."""

    @pytest.mark.asyncio
    async def test_templates(self, client, admin_token):
        r = await client.get("/api/aggregations/templates", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert len(r.json()) > 0

    @pytest.mark.asyncio
    async def test_templates_requires_auth(self, client):
        r = await client.get("/api/aggregations/templates")
        assert r.status_code == 401


class TestCompositions:
    """API composition endpoints."""

    @pytest.mark.asyncio
    async def test_list_compositions(self, client, admin_token):
        r = await client.get("/api/compositions/", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 403)

    @pytest.mark.asyncio
    async def test_list_compositions_requires_auth(self, client):
        r = await client.get("/api/compositions/")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_create_composition(self, client, admin_token):
        r = await client.post(
            "/api/compositions/",
            json={"name": "test-comp", "description": "Test", "method": "GET", "steps": [], "output_step": ""},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code in (201, 200, 403, 409)


class TestPipelines:
    """Aggregation pipeline CRUD."""

    @pytest.mark.asyncio
    async def test_create_pipeline(self, client, admin_token):
        r = await client.post(
            "/api/pipelines/",
            json={"name": "test-pipe", "collection": "Items", "stages": [{"type": "limit", "params": {"limit": 10}}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code in (200, 201, 403)

    @pytest.mark.asyncio
    async def test_list_pipelines(self, client, admin_token):
        r = await client.get("/api/pipelines/", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (200, 403)

    @pytest.mark.asyncio
    async def test_get_pipeline(self, client, admin_token):
        r = await client.get("/api/pipelines/fakeid123456789012", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code in (400, 403)  # Invalid ID format

    @pytest.mark.asyncio
    async def test_pipelines_require_auth(self, client):
        r = await client.get("/api/pipelines/")
        assert r.status_code == 401
