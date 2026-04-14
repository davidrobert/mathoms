"""Shared test fixtures for backend tests."""

import asyncio
import os
from typing import AsyncGenerator

_TEST_FERNET_KEY = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="
os.environ.setdefault("FIN_FERNET_KEY", _TEST_FERNET_KEY)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.database import Base, get_db
import backend.app.models  # noqa: F401 — ensure ALL models register with Base.metadata
from backend.app.core.config import settings
from backend.app.main import app

if not settings.FERNET_KEY:
    settings.FERNET_KEY = _TEST_FERNET_KEY

TEST_DB_URL = "sqlite+aiosqlite://"

engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    poolclass=pool.StaticPool,
    connect_args={"check_same_thread": False},
)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Raw async DB session for model-level tests."""
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    """Client with a pre-registered, authenticated user."""
    resp = await client.post("/api/auth/register", json={
        "email": "fixture@test.com",
        "password": "testpass123",
        "full_name": "Fixture User",
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
