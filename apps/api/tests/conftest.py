from __future__ import annotations

import os
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _override_env():
    os.environ.update({
        "ENV": "dev",
        "JWT_SECRET": "test-secret-key-must-be-32bytes!",
        "ADMIN_EMAIL": "admin@admin.com",
        "AUTH_DEV_FALLBACK": "true",
        "DATABASE_URL": "postgresql+asyncpg://aiagent:aiagent@localhost:5432/aiagent",
        "REDIS_URL": "",
        "WEB_ORIGIN": "http://localhost:5173",
        "LLM_PROVIDER": "mock",
        "GEMINI_API_KEY": "",
        "MCP_URL": "http://mcp:8000/mcp",
    })
    yield


@pytest.fixture
async def client():
    from src.app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient):
    response = await client.post("/auth/login", json={"email": "user@test.com"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_headers(client: AsyncClient):
    response = await client.post("/auth/login", json={"email": "admin@admin.com"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
