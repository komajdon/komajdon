from __future__ import annotations

import pytest


class TestSDK:
    """SDK generation endpoints."""

    @pytest.mark.asyncio
    async def test_typescript_sdk(self, client, admin_token, mock_db):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": "Widget",
            "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "count", "type": "number"},
            ],
            "created_at": "now",
        })
        r = await client.get("/api/sdk/Widget", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert "WidgetApi" in r.text
        assert "interface Widget" in r.text

    @pytest.mark.asyncio
    async def test_python_sdk(self, client, admin_token, mock_db):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": "Gadget", "fields": [{"name": "name", "type": "string"}], "created_at": "now",
        })
        r = await client.get("/api/sdk/Gadget?lang=python", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert "class Gadget" in r.text
        assert "def list" in r.text

    @pytest.mark.asyncio
    async def test_javascript_sdk(self, client, admin_token, mock_db):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": "Doodad", "fields": [{"name": "name", "type": "string"}], "created_at": "now",
        })
        r = await client.get("/api/sdk/Doodad?lang=javascript", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert "class DoodadApi" in r.text

    @pytest.mark.asyncio
    async def test_curl_snippets(self, client, admin_token, mock_db):
        schemas = mock_db("_schemas")
        await schemas.insert_one({
            "name": "Thing", "fields": [{"name": "name", "type": "string"}], "created_at": "now",
        })
        r = await client.get("/api/sdk/Thing?lang=curl", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert "curl" in r.text

    @pytest.mark.asyncio
    async def test_sdk_model_not_found(self, client, admin_token):
        r = await client.get("/api/sdk/NonExistent", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_sdk_requires_auth(self, client):
        r = await client.get("/api/sdk/Widget")
        assert r.status_code == 401


class TestApiKeys:
    """API key management endpoints."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, client, admin_token):
        r = await client.post("/api/keys/?name=test-key&role=viewer", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 201
        assert "key" in r.json()
        assert r.json()["key"].startswith("mf_")

    @pytest.mark.asyncio
    async def test_list_api_keys(self, client, admin_token):
        await client.post("/api/keys/?name=k1&role=viewer", headers={"Authorization": f"Bearer {admin_token}"})
        r = await client.get("/api/keys/", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_delete_api_key(self, client, admin_token):
        r = await client.post("/api/keys/?name=del-key&role=viewer", headers={"Authorization": f"Bearer {admin_token}"})
        key_id = r.json().get("id")
        if key_id:
            r2 = await client.delete(f"/api/keys/{key_id}", headers={"Authorization": f"Bearer {admin_token}"})
            assert r2.status_code == 200

    @pytest.mark.asyncio
    async def test_api_key_requires_auth(self, client):
        r = await client.post("/api/keys/?name=no&role=viewer")
        assert r.status_code == 401
