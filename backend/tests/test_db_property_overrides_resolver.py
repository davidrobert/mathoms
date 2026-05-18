"""Tests — `DBPropertyOverridesResolver` (ADR-215 P3 connection fix).

Cobre o caminho que conecta `workspace_property_overrides` (gravado pelo
endpoint P4 / UI P5) ao pipeline E5 via injeção em `WorkspaceContext`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import (
    CLASSIFICATION_LOCADO,
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    CLASSIFICATION_USO_PESSOAL,
    OVERRIDE_SOURCE_USER_MANUAL,
    PropertyIdentity,
    User,
    Workspace,
    WorkspacePropertyOverride,
)
from backend.app.services.db_property_overrides_resolver import (
    DBPropertyOverridesResolver,
)
from pipeline.ports import PropertyOverridesResolver


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_dbpor.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


def _seed_workspace(factory, ws_id: str | None = None) -> Workspace:
    ws_id = ws_id or str(uuid.uuid4())
    with factory() as s:
        user = User(
            id=str(uuid.uuid4()),
            email=f"u-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password="x",
            full_name="Test",
        )
        s.add(user)
        s.flush()
        ws = Workspace(id=ws_id, name="Test WS", owner_id=user.id)
        s.add(ws)
        s.commit()
        s.refresh(ws)
        return ws


def _seed_property(factory, ws: Workspace, *, descricao: str = "casa-x") -> PropertyIdentity:
    with factory() as s:
        prop = PropertyIdentity(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            titular_key="david_robert",
            codigo_rfb="12",
            endereco_canonical=descricao,
            first_seen_year=2024,
            descricao_sample=descricao,
            low_confidence=False,
            created_at=datetime.now(timezone.utc),
        )
        s.add(prop)
        s.commit()
        s.refresh(prop)
        return prop


def _seed_override(
    factory,
    *,
    ws: Workspace,
    prop: PropertyIdentity,
    classification: str,
) -> None:
    with factory() as s:
        row = WorkspacePropertyOverride(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            property_id=prop.id,
            classification=classification,
            override_source=OVERRIDE_SOURCE_USER_MANUAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        s.add(row)
        s.commit()


def test_satisfies_protocol(sync_db):
    with sync_db() as session:
        resolver = DBPropertyOverridesResolver(session=session)
        assert isinstance(resolver, PropertyOverridesResolver)


def test_empty_workspace_returns_empty_dict(sync_db):
    ws = _seed_workspace(sync_db)
    with sync_db() as session:
        resolver = DBPropertyOverridesResolver(session=session)
        assert resolver.list_for_workspace(ws.id) == {}


def test_returns_classification_by_property_id(sync_db):
    ws = _seed_workspace(sync_db)
    prop = _seed_property(sync_db, ws)
    _seed_override(sync_db, ws=ws, prop=prop, classification=CLASSIFICATION_RESIDENCIA_PRINCIPAL)
    with sync_db() as session:
        resolver = DBPropertyOverridesResolver(session=session)
        result = resolver.list_for_workspace(ws.id)
        assert result == {prop.id: CLASSIFICATION_RESIDENCIA_PRINCIPAL}


def test_returns_all_overrides_for_workspace(sync_db):
    ws = _seed_workspace(sync_db)
    p1 = _seed_property(sync_db, ws, descricao="casa-a")
    p2 = _seed_property(sync_db, ws, descricao="casa-b")
    p3 = _seed_property(sync_db, ws, descricao="terreno-c")
    _seed_override(sync_db, ws=ws, prop=p1, classification=CLASSIFICATION_RESIDENCIA_PRINCIPAL)
    _seed_override(sync_db, ws=ws, prop=p2, classification=CLASSIFICATION_LOCADO)
    _seed_override(sync_db, ws=ws, prop=p3, classification=CLASSIFICATION_USO_PESSOAL)
    with sync_db() as session:
        resolver = DBPropertyOverridesResolver(session=session)
        result = resolver.list_for_workspace(ws.id)
        assert result == {
            p1.id: CLASSIFICATION_RESIDENCIA_PRINCIPAL,
            p2.id: CLASSIFICATION_LOCADO,
            p3.id: CLASSIFICATION_USO_PESSOAL,
        }


def test_isolates_workspaces(sync_db):
    ws1 = _seed_workspace(sync_db)
    ws2 = _seed_workspace(sync_db)
    p1 = _seed_property(sync_db, ws1, descricao="casa-ws1")
    p2 = _seed_property(sync_db, ws2, descricao="casa-ws2")
    _seed_override(sync_db, ws=ws1, prop=p1, classification=CLASSIFICATION_RESIDENCIA_PRINCIPAL)
    _seed_override(sync_db, ws=ws2, prop=p2, classification=CLASSIFICATION_LOCADO)
    with sync_db() as session:
        resolver = DBPropertyOverridesResolver(session=session)
        assert resolver.list_for_workspace(ws1.id) == {p1.id: CLASSIFICATION_RESIDENCIA_PRINCIPAL}
        assert resolver.list_for_workspace(ws2.id) == {p2.id: CLASSIFICATION_LOCADO}
