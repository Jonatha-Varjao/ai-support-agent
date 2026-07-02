from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.skip(reason="Requires running PostgreSQL + Redis.")
async def test_delete_own_thread(client: AsyncClient, auth_headers: dict):
    response = await client.get("/threads", headers=auth_headers)
    threads = response.json()
    if not threads:
        pytest.skip("No threads to delete")
    thread_id = threads[0]["id"]

    response = await client.delete(f"/threads/{thread_id}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get("/threads", headers=auth_headers)
    ids = [t["id"] for t in response.json()]
    assert thread_id not in ids
