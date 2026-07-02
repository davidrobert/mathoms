"""Shared fixtures for pipeline-service tests.

Pipeline-service runs from its own directory in CI; tests here need:
- repo root on sys.path so `pipeline.*` resolves;
- `pipeline-service/` on sys.path so `app.*` resolves without `pip install -e`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVICE_ROOT.parent
for p in (_SERVICE_ROOT, _REPO_ROOT):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

import pytest
from app.main import create_app  # noqa: E402
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client for unit-level HTTP tests."""
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _reset_event_client():
    """Reset Redis singleton between tests to avoid fixture bleed."""
    from app.services import event_publisher

    event_publisher.reset_client()
    yield
    event_publisher.reset_client()


@pytest.fixture(autouse=True)
def artifact_db_session_factory(monkeypatch):
    """SQLite em memória por teste para o ``DBArtifactStore`` (ADR-303).

    Autouse: sem isso, ``open_artifact_store`` abriria sessão contra o
    engine default do backend (arquivo ``mathoms.db``) em qualquer teste
    que execute stage. Engine local por teste — sem estado compartilhado.
    """
    from app.services import artifact_session
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import backend.app.models  # noqa: F401 — registra tabelas no metadata
    from backend.app.core.database import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(artifact_session, "_new_session", lambda: factory())
    yield factory
    engine.dispose()
