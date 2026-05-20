from __future__ import annotations

import pytest


class TestRoles:
    """Role management endpoints."""

    @pytest.mark.asyncio
    async def test_list_permissions(self, client, admin_token):
        r = await client.get("/api/roles/permissions", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert len(r.json()) > 0

    @pytest.mark.asyncio
    async def test_list_permissions_forbidden(self, client, user_token):
        r = await client.get("/api/roles/permissions", headers={"Authorization": f"Bearer {user_token}"})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_list_roles(self, client, admin_token):
        r = await client.get("/api/roles/", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_create_role(self, client, admin_token):
        r = await client.post(
            "/api/roles/",
            json={"name": "custom-role", "description": "A test role", "permissions": ["api:access", "*:read"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 201

    @pytest.mark.asyncio
    async def test_create_role_duplicate(self, client, admin_token):
        await client.post(
            "/api/roles/",
            json={"name": "dup-role", "permissions": ["api:access"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        r = await client.post(
            "/api/roles/",
            json={"name": "dup-role", "permissions": ["api:access"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_get_role(self, client, admin_token, mock_db):
        roles = mock_db("_roles")
        await roles.insert_one({"name": "get-role", "permissions": ["api:access"], "is_default": False, "created_at": "now"})
        r = await client.get("/api/roles/", headers={"Authorization": f"Bearer {admin_token}"})
        roles_list = r.json()
        if roles_list:
            rid = roles_list[0]["id"]
            r2 = await client.get(f"/api/roles/{rid}", headers={"Authorization": f"Bearer {admin_token}"})
            assert r2.status_code == 200
            assert "name" in r2.json()

    @pytest.mark.asyncio
    async def test_update_role(self, client, admin_token, mock_db):
        roles = mock_db("_roles")
        await roles.insert_one({"name": "upd-role", "permissions": ["api:access"], "is_default": False, "created_at": "now"})
        r = await client.get("/api/roles/", headers={"Authorization": f"Bearer {admin_token}"})
        roles_list = r.json()
        if roles_list:
            rid = roles_list[0]["id"]
            r2 = await client.put(
                f"/api/roles/{rid}",
                json={"description": "Updated description"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r2.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_role(self, client, admin_token, mock_db):
        roles = mock_db("_roles")
        await roles.insert_one({"name": "del-role", "permissions": ["api:access"], "is_default": False, "created_at": "now"})
        r = await client.get("/api/roles/", headers={"Authorization": f"Bearer {admin_token}"})
        targets = [x for x in r.json() if x["name"] == "del-role"]
        if targets:
            r2 = await client.delete(f"/api/roles/{targets[0]['id']}", headers={"Authorization": f"Bearer {admin_token}"})
            assert r2.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_default_role_fails(self, client, admin_token, mock_db):
        roles = mock_db("_roles")
        await roles.insert_one({"name": "default-role", "permissions": ["api:access"], "is_default": True, "created_at": "now"})
        r = await client.get("/api/roles/", headers={"Authorization": f"Bearer {admin_token}"})
        targets = [x for x in r.json() if x.get("is_default")]
        if targets:
            r2 = await client.delete(f"/api/roles/{targets[0]['id']}", headers={"Authorization": f"Bearer {admin_token}"})
            assert r2.status_code == 400
