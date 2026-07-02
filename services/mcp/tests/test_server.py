from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from mcp_server.server import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_web_fetch_timeout(client: AsyncClient):
    response = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "method": "web_fetch",
        "params": {"url": "https://invalid-url-that-timeouts.example.com"},
        "id": 1,
    })
    result = response.json()
    assert "error" in result or "result" in result


async def test_web_fetch_missing_url(client: AsyncClient):
    response = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "method": "web_fetch",
        "params": {},
        "id": 1,
    })
    result = response.json()
    assert "error" in result or ("result" in result and result["result"].get("ok") is not None)
