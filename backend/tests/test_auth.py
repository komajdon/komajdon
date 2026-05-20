from __future__ import annotations

import pytest


class TestAuthPublic:
    """Public auth endpoints: signup, signin, login, register."""

    @pytest.mark.asyncio
    async def test_signup(self, client, mock_db):
        r = await client.post("/api/auth/signup", json={"email": "new@test.com", "password": "NewPass123!"})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "new@test.com"
        assert data["user"]["role"] == "user"

    @pytest.mark.asyncio
    async def test_signup_duplicate_email(self, client, mock_db):
        await client.post("/api/auth/signup", json={"email": "dup@test.com", "password": "DupPass123!"})
        r = await client.post("/api/auth/signup", json={"email": "dup@test.com", "password": "DupPass123!"})
        assert r.status_code == 400
        assert "already registered" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_signup_weak_password(self, client, mock_db):
        r = await client.post("/api/auth/signup", json={"email": "weak@test.com", "password": "short"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_no_uppercase(self, client, mock_db):
        r = await client.post("/api/auth/signup", json={"email": "no@test.com", "password": "alllowercase1"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_no_digit(self, client, mock_db):
        r = await client.post("/api/auth/signup", json={"email": "nod@test.com", "password": "NoDigitsHere"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_missing_email(self, client, mock_db):
        r = await client.post("/api/auth/signup", json={"password": "Valid1234"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_signin(self, client, mock_db):
        await client.post("/api/auth/signup", json={"email": "si@test.com", "password": "Signin123!"})
        r = await client.post("/api/auth/signin", json={"email": "si@test.com", "password": "Signin123!"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    @pytest.mark.asyncio
    async def test_signin_wrong_password(self, client, mock_db):
        await client.post("/api/auth/signup", json={"email": "wp@test.com", "password": "WrongPw123!"})
        r = await client.post("/api/auth/signin", json={"email": "wp@test.com", "password": "BadPass123!"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_signin_nonexistent_user(self, client, mock_db):
        r = await client.post("/api/auth/signin", json={"email": "nobody@test.com", "password": "Nope1234!"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_login_alias(self, client, mock_db):
        await client.post("/api/auth/signup", json={"email": "la@test.com", "password": "LoginAb123!"})
        r = await client.post("/api/auth/login", json={"email": "la@test.com", "password": "LoginAb123!"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_register_alias(self, client, mock_db):
        r = await client.post("/api/auth/register", json={"email": "ra@test.com", "password": "RegAlias1!"})
        assert r.status_code == 200


class TestAuthAuthenticated:
    """Authenticated endpoints: me, refresh, logout."""

    @pytest.mark.asyncio
    async def test_me(self, client, user_token):
        r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {user_token}"})
        assert r.status_code == 200
        assert r.json()["email"] == "user@test.com"

    @pytest.mark.asyncio
    async def test_me_no_token(self, client):
        r = await client.get("/api/auth/me")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, client):
        r = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh(self, client, mock_db):
        r = await client.post("/api/auth/signup", json={"email": "rf@test.com", "password": "Ref12345!"})
        tokens = r.json()
        refresh = tokens["refresh_token"]
        r2 = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert r2.status_code == 200
        assert "access_token" in r2.json()

    @pytest.mark.asyncio
    async def test_refresh_invalid(self, client):
        r = await client.post("/api/auth/refresh", json={"refresh_token": "bad-refresh-token"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_logout(self, client, user_token, mock_db):
        r = await client.post(
            "/api/auth/logout",
            json={"refresh_token": "some-refresh-token"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r.status_code == 200
        assert r.json()["message"] == "Logged out"


class TestAuthVerification:
    """Email verification and password reset."""

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, client):
        r = await client.post("/api/auth/verify-email", json={"token": "bad-token"})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_resend_verification(self, client, user_token):
        r = await client.post(
            "/api/auth/resend-verification",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_forgot_password(self, client):
        r = await client.post("/api/auth/forgot-password", json={"email": "anyone@test.com"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, client):
        r = await client.post("/api/auth/reset-password", json={"token": "bad", "new_password": "NewPass1234!"})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_weak(self, client):
        r = await client.post("/api/auth/reset-password", json={"token": "x", "new_password": "short"})
        assert r.status_code == 400


class TestAuthAccountLockout:
    """Account lockout after 5 failed attempts."""

    @pytest.mark.asyncio
    async def test_account_locked_after_5_fails(self, client, mock_db):
        await client.post("/api/auth/signup", json={"email": "lock@test.com", "password": "LockOut1!"})
        for _ in range(5):
            await client.post("/api/auth/signin", json={"email": "lock@test.com", "password": "wrong"})
        r = await client.post("/api/auth/signin", json={"email": "lock@test.com", "password": "LockOut1!"})
        assert r.status_code == 423
        assert "locked" in r.json()["detail"].lower()


class TestAuthAdmin:
    """Admin user management endpoints."""

    @pytest.mark.asyncio
    async def test_list_users(self, client, admin_token):
        r = await client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_list_users_forbidden(self, client, user_token):
        r = await client.get("/api/auth/users", headers={"Authorization": f"Bearer {user_token}"})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_create_user_manual(self, client, admin_token):
        r = await client.post(
            "/api/auth/users",
            json={"email": "manual@test.com", "password": "Manual123!", "role": "viewer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 201
        assert r.json()["user"]["email"] == "manual@test.com"

    @pytest.mark.asyncio
    async def test_get_user(self, client, admin_token, mock_db):
        users = mock_db("users")
        await users.insert_one({"email": "g@t.com", "role": "user", "permissions": [], "created_at": "now"})
        r = await client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
        users_list = r.json()
        uid = users_list[0]["id"]
        r2 = await client.get(f"/api/auth/users/{uid}", headers={"Authorization": f"Bearer {admin_token}"})
        assert r2.status_code == 200

    @pytest.mark.asyncio
    async def test_update_user_role(self, client, admin_token, mock_db):
        await client.post(
            "/api/auth/users",
            json={"email": "role@test.com", "password": "Role1234!", "role": "user"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        users = await client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
        uid = users.json()[0]["id"]
        r = await client.patch(
            f"/api/auth/users/{uid}/role",
            json={"role": "viewer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_user(self, client, admin_token, mock_db):
        await client.post(
            "/api/auth/users",
            json={"email": "del@test.com", "password": "Del1234!", "role": "user"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        r = await client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
        targets = [u for u in r.json() if u["email"] == "del@test.com"]
        if targets:
            r2 = await client.delete(f"/api/auth/users/{targets[0]['id']}", headers={"Authorization": f"Bearer {admin_token}"})
            assert r2.status_code == 200

    @pytest.mark.asyncio
    async def test_update_user(self, client, admin_token, mock_db):
        r = await client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
        if r.json():
            uid = r.json()[0]["id"]
            r2 = await client.patch(
                f"/api/auth/users/{uid}",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r2.status_code == 200
