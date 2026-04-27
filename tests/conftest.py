import pytest
import asyncio
from httpx import AsyncClient
from typing import AsyncGenerator
from app.main import app
from app.core.security import create_access_token
import uuid

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

import pytest_asyncio
from httpx import AsyncClient, ASGITransport

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def auth_headers():
    def _auth_headers(user_id: str):
        token = create_access_token(user_id)
        return {"Authorization": f"Bearer {token}"}
    return _auth_headers

@pytest.fixture
def test_user_id():
    return "f412f236-4edc-47a2-8f54-8763a6ed2ce8"
