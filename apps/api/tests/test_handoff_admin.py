from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_admin_can_list_handoffs(client: AsyncClient, admin_headers: dict):
    response = await client.get("/admin/handoffs", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_admin_can_filter_handoffs_by_status(
    client: AsyncClient, admin_headers: dict
):
    response = await client.get("/admin/handoffs?status=open", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_non_admin_cannot_access_handoffs(
    client: AsyncClient, auth_headers: dict
):
    response = await client.get("/admin/handoffs", headers=auth_headers)
    assert response.status_code == 403
