"""ADR-215 P1: model-level tests for PropertyIdentity + WorkspacePropertyOverride."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    CLASSIFICATION_LOCADO,
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    CLASSIFICATION_USO_PESSOAL,
    OVERRIDE_SOURCE_USER_MANUAL,
    RESIDENCIA_STATUS_OWNED,
    RESIDENCIA_STATUS_UNDECLARED,
    PropertyIdentity,
    User,
    Workspace,
    WorkspacePropertyOverride,
)


async def _make_workspace(db: AsyncSession) -> Workspace:
    user = User(
        id=str(uuid.uuid4()),
        email=f"test-{uuid.uuid4().hex[:8]}@property.com",
        hashed_password="x",
        full_name="Test",
    )
    db.add(user)
    await db.flush()
    ws = Workspace(
        id=str(uuid.uuid4()),
        name="Test WS",
        owner_id=user.id,
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws


async def _make_property(db: AsyncSession, ws: Workspace, **kwargs) -> PropertyIdentity:
    p = PropertyIdentity(
        workspace_id=ws.id,
        titular_key="david_robert",
        codigo_rfb="12",
        endereco_canonical="rua tasso da silveira 61",
        first_seen_year=2024,
        descricao_sample="CASA - RUA TASSO DA SILVEIRA, 61",
        **kwargs,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest.mark.asyncio
async def test_workspace_defaults_to_undeclared_residencia_status(db: AsyncSession):
    ws = await _make_workspace(db)
    fetched = (await db.execute(select(Workspace).where(Workspace.id == ws.id))).scalar_one()
    assert fetched.residencia_status == RESIDENCIA_STATUS_UNDECLARED


@pytest.mark.asyncio
async def test_property_identity_crud(db: AsyncSession):
    ws = await _make_workspace(db)
    p = await _make_property(db, ws)
    assert p.id is not None
    assert p.workspace_id == ws.id
    assert p.low_confidence is False
    assert p.codigo_rfb == "12"


@pytest.mark.asyncio
async def test_override_persists_and_links_property(db: AsyncSession):
    ws = await _make_workspace(db)
    p = await _make_property(db, ws)
    o = WorkspacePropertyOverride(
        workspace_id=ws.id,
        property_id=p.id,
        classification=CLASSIFICATION_RESIDENCIA_PRINCIPAL,
        override_source=OVERRIDE_SOURCE_USER_MANUAL,
    )
    db.add(o)
    await db.commit()
    await db.refresh(o)
    assert o.id is not None
    assert o.classification == CLASSIFICATION_RESIDENCIA_PRINCIPAL


@pytest.mark.asyncio
async def test_one_residencia_principal_per_workspace_enforced(db: AsyncSession):
    """Partial unique index — não pode haver 2 residencia_principal no mesmo workspace."""
    ws = await _make_workspace(db)
    p1 = await _make_property(db, ws)
    # Segundo imóvel — endereço canonical diferente para passar lookup index.
    p2 = PropertyIdentity(
        workspace_id=ws.id,
        titular_key="david_robert",
        codigo_rfb="11",
        endereco_canonical="av paulista 1500",
        first_seen_year=2024,
        descricao_sample="APTO PAULISTA",
    )
    db.add(p2)
    await db.commit()

    db.add(
        WorkspacePropertyOverride(
            workspace_id=ws.id,
            property_id=p1.id,
            classification=CLASSIFICATION_RESIDENCIA_PRINCIPAL,
            override_source=OVERRIDE_SOURCE_USER_MANUAL,
        )
    )
    await db.commit()

    # Tentar marcar segundo como residencia_principal deve quebrar a partial unique.
    db.add(
        WorkspacePropertyOverride(
            workspace_id=ws.id,
            property_id=p2.id,
            classification=CLASSIFICATION_RESIDENCIA_PRINCIPAL,
            override_source=OVERRIDE_SOURCE_USER_MANUAL,
        )
    )
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_multiple_non_residencia_classifications_allowed(db: AsyncSession):
    """Partial unique só restringe residencia_principal — outros classifications podem repetir."""
    ws = await _make_workspace(db)
    p1 = await _make_property(db, ws)
    p2 = PropertyIdentity(
        workspace_id=ws.id,
        titular_key="david_robert",
        codigo_rfb="11",
        endereco_canonical="av paulista 1500",
        first_seen_year=2024,
        descricao_sample="APTO PAULISTA",
    )
    db.add(p2)
    await db.commit()

    db.add(
        WorkspacePropertyOverride(
            workspace_id=ws.id,
            property_id=p1.id,
            classification=CLASSIFICATION_LOCADO,
            override_source=OVERRIDE_SOURCE_USER_MANUAL,
        )
    )
    db.add(
        WorkspacePropertyOverride(
            workspace_id=ws.id,
            property_id=p2.id,
            classification=CLASSIFICATION_LOCADO,
            override_source=OVERRIDE_SOURCE_USER_MANUAL,
        )
    )
    await db.commit()  # Não pode estourar.


@pytest.mark.asyncio
async def test_classification_check_constraint_rejects_garbage(db: AsyncSession):
    ws = await _make_workspace(db)
    p = await _make_property(db, ws)
    db.add(
        WorkspacePropertyOverride(
            workspace_id=ws.id,
            property_id=p.id,
            classification="garbage_value",
            override_source=OVERRIDE_SOURCE_USER_MANUAL,
        )
    )
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_workspace_can_be_set_to_owned_status(db: AsyncSession):
    ws = await _make_workspace(db)
    ws.residencia_status = RESIDENCIA_STATUS_OWNED
    await db.commit()
    await db.refresh(ws)
    assert ws.residencia_status == RESIDENCIA_STATUS_OWNED


def test_fk_declares_ondelete_cascade_to_workspace():
    """FK property_identity.workspace_id e workspace_property_overrides.workspace_id
    devem declarar ON DELETE CASCADE (prod usa Postgres com FKs ativos).

    NOTA: tests usam SQLite com FK pragma OFF intencionalmente (ver
    backend/app/core/database.py:33). Por isso testamos a declaração do
    FK, não a execução do cascade.
    """
    pi_fks = list(PropertyIdentity.__table__.c.workspace_id.foreign_keys)
    wpo_ws_fks = list(WorkspacePropertyOverride.__table__.c.workspace_id.foreign_keys)
    wpo_prop_fks = list(WorkspacePropertyOverride.__table__.c.property_id.foreign_keys)

    assert pi_fks and pi_fks[0].ondelete == "CASCADE"
    assert wpo_ws_fks and wpo_ws_fks[0].ondelete == "CASCADE"
    assert wpo_prop_fks and wpo_prop_fks[0].ondelete == "CASCADE"
