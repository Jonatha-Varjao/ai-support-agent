from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_admin_can_create_kb_entry(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/admin/kb",
        json={
            "category": "faq",
            "title": "Test entry",
            "content": "Test content for the KB.",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test entry"
    assert data["category"] == "faq"


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_admin_can_list_kb(client: AsyncClient, admin_headers: dict):
    response = await client.get("/admin/kb", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_non_admin_cannot_create_kb(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/admin/kb",
        json={"category": "faq", "title": "Test", "content": "Test content"},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_admin_can_delete_kb_entry(client: AsyncClient, admin_headers: dict):
    # Create then delete
    create_resp = await client.post(
        "/admin/kb",
        json={"category": "faq", "title": "ToDelete", "content": "Delete me"},
        headers=admin_headers,
    )
    kid = create_resp.json()["id"]

    delete_resp = await client.delete(f"/admin/kb/{kid}", headers=admin_headers)
    assert delete_resp.status_code == 204


@pytest.mark.skip(reason="Requires running PostgreSQL.")
async def test_admin_can_filter_by_category(client: AsyncClient, admin_headers: dict):
    response = await client.get("/admin/kb?category=faq", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["category"] == "faq"
