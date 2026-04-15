"""Shared test fixtures for backend tests.

# Test DB isolation strategy — F6.5 (sub-fase 6.5F.1)

ADR resumido (registro completo em `docs/DECISIONS.md` quando F6.5F formal):

**Decisão:** *recreate-per-test* sobre SQLite in-memory + StaticPool.

**Alternativas avaliadas:**
1. *recreate* (drop_all + create_all em cada test) — escolhida.
2. *transaction-rollback* (BEGIN no setup, ROLLBACK no teardown) — descartada
   por incompatibilidade com SAVEPOINTs em SQLite + complexidade com nested
   sessions e Celery.
3. *truncate* — descartada para SQLite (sem TRUNCATE nativo) e prematura
   para PostgreSQL (que vem em F7).

**Por que *recreate* aqui:**
- SQLite in-memory é instantâneo (~5-10ms por test). Sem ganho real ao
  otimizar.
- Isolation perfeita: cada teste vê schema limpo; impossível leak entre
  testes.
- Trivial de raciocinar — se um test passa sozinho mas falha junto, é
  bug do test, não da infra.

**Quando migrar:**
- Se aparecer >100 testes que dependem de PG-only features (ARRAY, JSONB,
  CTEs específicas), ADR-novo decide entre *transaction-rollback* (rápido)
  ou Postgres ephemeral por test (preciso, lento). Hoje (F6.5) não.

**Convenções para autores de testes:**
- Use a fixture `db` para acesso direto ao DB.
- Use `client` para testes de endpoint sem auth.
- Use `auth_client` quando precisar de Authorization Bearer.
- Use as factories em `backend/tests/factories/` (F6.5F.2) ao criar dados;
  evite construir models à mão — quebra ao mudar schema.
"""

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
    """Recreate schema before every test and drop after.

    Documented in module docstring above (sub-fase 6.5F.1).
    """
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
    """Client with a pre-registered, authenticated user.

    NOTE: Para tests de multi-tenant isolation (6.5B.12), use a factory
    `make_user(db, ...)` + `make_workspace(db, owner=user)` e crie tokens
    via `backend.app.core.security.create_access_token(user.id)` para evitar
    colidir nesse fixture pré-fabricado.
    """
    resp = await client.post("/api/auth/register", json={
        "email": "fixture@test.com",
        "password": "testpass123",
        "full_name": "Fixture User",
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ─── Factories — exported for ergonomic test setup (F6.5F.2) ────────────
# Re-export `factories` namespace so tests can do:
#   from backend.tests.conftest import factories
#   user = await factories.make_user(db, email="x@test.com")
# Or import directly from backend.tests.factories.

from backend.tests import factories  # noqa: E402,F401
