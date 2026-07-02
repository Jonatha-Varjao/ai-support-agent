from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_admin_can_list_unanswered(client: AsyncClient, admin_headers: dict):
    response = await client.get("/admin/unanswered", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_non_admin_cannot_list_unanswered(client: AsyncClient, auth_headers: dict):
    response = await client.get("/admin/unanswered", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_admin_can_filter_by_reason(client: AsyncClient, admin_headers: dict):
    response = await client.get("/admin/unanswered?reason=injection", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["reason"] == "injection"
