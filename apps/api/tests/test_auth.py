from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_login_dev_fallback(client: AsyncClient):
    response = await client.post("/auth/login", json={"email": "user@test.com"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "user@test.com"
    assert data["user"]["role"] == "user"
    assert data["user"]["id"] != "dev"


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_login_admin_email_gets_admin_role(client: AsyncClient):
    response = await client.post("/auth/login", json={"email": "admin@admin.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "admin"


async def test_login_invalid_email(client: AsyncClient):
    response = await client.post("/auth/login", json={"email": "not-an-email"})
    assert response.status_code == 422


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_me_with_valid_token(client: AsyncClient):
    login_resp = await client.post("/auth/login", json={"email": "user@test.com"})
    token = login_resp.json()["access_token"]

    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@test.com"


async def test_me_without_token(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_with_invalid_token(client: AsyncClient):
    response = await client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_login_creates_user_and_returns_real_id(client: AsyncClient):
    """Login must create a real User row and return a valid UUID in the response."""
    response = await client.post("/auth/login", json={"email": "newuser@test.com"})
    assert response.status_code == 200
    data = response.json()
    uid = data["user"]["id"]
    assert uid != "dev"
    assert uid != "unknown"
    # UUID format: 8-4-4-4-12 hex chars
    assert len(uid) == 36
    assert uid.count("-") == 4


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_login_existing_user_returns_same_id(client: AsyncClient):
    """Logging in twice with the same email returns the same user.id."""
    resp1 = await client.post("/auth/login", json={"email": "same@test.com"})
    resp2 = await client.post("/auth/login", json={"email": "same@test.com"})
    assert resp1.json()["user"]["id"] == resp2.json()["user"]["id"]
