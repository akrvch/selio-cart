import os
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_healthz():
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


