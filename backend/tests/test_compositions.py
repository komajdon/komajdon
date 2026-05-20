from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_compositions_list_requires_auth(client: AsyncClient):
    response = await client.get("/api/compositions/")
    assert response.status_code == 401
