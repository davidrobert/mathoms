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
import atexit
import os
import tempfile
import uuid as _uuid
from pathlib import Path
from typing import AsyncGenerator

_TEST_FERNET_KEY = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="
os.environ.setdefault("MATHOMS_FERNET_KEY", _TEST_FERNET_KEY)

# scripts.pipeline_common requires MATHOMS_WORKSPACE_ROOT; repo root for config/ in tests.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
os.environ.setdefault("MATHOMS_WORKSPACE_ROOT", str(_REPO_ROOT))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

import backend.app.core.database as _database_module
import backend.app.models  # noqa: F401 — ensure ALL models register with Base.metadata
from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.main import app

if not settings.FERNET_KEY:
    settings.FERNET_KEY = _TEST_FERNET_KEY

# File-backed SQLite so the async engine (aiosqlite) and the sync engine
# (SyncSessionLocal, used by code paths reached through endpoints — e.g.
# config_materializer.ensure_tenant_pipeline_config, pipeline_service.*)
# share the same schema and data. Pure in-memory would require shared raw
# connections across drivers, which SQLAlchemy doesn't support.
_TEST_DB_FILE = Path(tempfile.gettempdir()) / f"mathoms_test_{_uuid.uuid4().hex}.db"
atexit.register(lambda: _TEST_DB_FILE.unlink(missing_ok=True))

TEST_DB_URL = f"sqlite+aiosqlite:///{_TEST_DB_FILE}"
TEST_SYNC_DB_URL = f"sqlite:///{_TEST_DB_FILE}"

engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    poolclass=pool.StaticPool,
    connect_args={"check_same_thread": False},
)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

_sync_test_engine = create_engine(
    TEST_SYNC_DB_URL,
    echo=False,
    poolclass=pool.StaticPool,
    connect_args={"check_same_thread": False},
)
TestSyncSession = sessionmaker(bind=_sync_test_engine, expire_on_commit=False)

# Patch every module that imported SyncSessionLocal at top-level — their local
# binding is independent and won't see a module-level mutation otherwise.
_database_module.SyncSessionLocal = TestSyncSession
_database_module.sync_engine = _sync_test_engine

from backend.app.scripts import backfill_artifacts_from_disk as _backfill_module  # noqa: E402
from backend.app.services import (
    document_pipeline_sync as _document_pipeline_sync_module,  # noqa: E402
)
from backend.app.services import pipeline_service as _pipeline_service_module  # noqa: E402
from backend.app.tasks import periodic_tasks as _periodic_tasks_module  # noqa: E402
from backend.app.tasks import pipeline_task as _pipeline_task_module  # noqa: E402

for _mod in (
    _pipeline_task_module,
    _periodic_tasks_module,
    _pipeline_service_module,
    _document_pipeline_sync_module,
    _backfill_module,
):
    _mod.SyncSessionLocal = TestSyncSession


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
    # Invalidate the sync engine's pooled connection so the next test sees the
    # fresh schema — StaticPool would otherwise hold a connection that still
    # references the dropped tables.
    _sync_test_engine.dispose()


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

    After F9/ADR-072 tenant-path migration, also exposes the auto-created
    workspace's id via ``client.ws_id`` so tests can build tenant-scoped
    URLs as ``f"/api/workspaces/{client.ws_id}/{resource}"``.

    NOTE: Para tests de multi-tenant isolation (6.5B.12), use a factory
    `make_user(db, ...)` + `make_workspace(db, owner=user)` e crie tokens
    via `backend.app.core.security.create_access_token(user.id)` para evitar
    colidir nesse fixture pré-fabricado.
    """
    from sqlalchemy import select

    from backend.app.models.workspace import Workspace

    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "fixture@test.com",
            "password": "testpass123",
            "full_name": "Fixture User",
        },
    )
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    # Resolve workspace id of the user (register auto-creates one).
    async with TestSession() as session:
        ws = (await session.execute(select(Workspace))).scalar_one()
        client.ws_id = ws.id  # type: ignore[attr-defined]
    return client


@pytest_asyncio.fixture
async def auth_client_with_doc(auth_client: AsyncClient) -> AsyncClient:
    """``auth_client`` with one ready document + a file in the tenant data dir.

    Required by tests that hit ``/api/pipeline/run`` — the endpoint blocks
    triggering the pipeline when the workspace has zero ``ready`` documents
    or no files under ``storage/<ws>/data/<group>/``.

    Creates the doc directly in the DB (bypasses the upload endpoint) and
    drops a 1-byte file in ``data/financial_statements/`` so both checks
    pass. The pipeline itself is always mocked in these tests; we just need
    the gate to let us through.
    """
    from sqlalchemy import select

    from backend.app.core.config import settings
    from backend.app.models.document import Document, DocumentStatus, DocumentType
    from backend.app.models.workspace import Workspace

    async with TestSession() as session:
        ws = (await session.execute(select(Workspace))).scalar_one()
        doc = Document(
            workspace_id=ws.id,
            original_name="fixture_extrato.pdf",
            stored_path="data/financial_statements/itau_extratoconta_202601_202602-0_original.pdf",
            doc_type=DocumentType.bank_statement,
            bank_code="itau",
            period="202601",
            status=DocumentStatus.ready,
            file_size_bytes=1,
            content_hash="fixture" + ws.id[:24],
        )
        session.add(doc)
        await session.commit()

        data_dir = settings.STORAGE_ROOT / ws.id / "data" / "financial_statements"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "itau_extratoconta_202601_202602-0_original.pdf").write_bytes(b"x")

    return auth_client


# ─── Factories — exported for ergonomic test setup (F6.5F.2) ────────────
# Re-export `factories` namespace so tests can do:
#   from backend.tests.conftest import factories
#   user = await factories.make_user(db, email="x@test.com")
# Or import directly from backend.tests.factories.

from backend.tests import factories  # noqa: E402,F401
