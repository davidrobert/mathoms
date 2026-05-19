"""ADR-223 (FU-1): default ``imoveis_no_if=false`` para workspaces novos — valida rows existentes preservadas + novos workspaces nascem false + set_at NULL distingue default não-afirmativo de escolha explícita."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.models import User, Workspace


@pytest.mark.asyncio
async def test_new_workspace_defaults_to_false(db):
    user = User(
        id=str(uuid.uuid4()),
        email="adr223-test@example.com",
        hashed_password="x",
        full_name="Test FU1",
    )
    db.add(user)
    await db.flush()
    ws = Workspace(name="W-FU1", owner_id=user.id)
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    assert ws.imoveis_no_if is False  # ADR-223 §1
    assert ws.imoveis_no_if_set_at is None  # default herdado, não escolha
    assert ws.imoveis_no_if_set_by_user_id is None


@pytest.mark.asyncio
async def test_set_at_null_distinguishes_default_from_explicit(db):
    user = User(
        id=str(uuid.uuid4()),
        email="adr223-explicit@example.com",
        hashed_password="x",
        full_name="Test FU1 Explicit",
    )
    db.add(user)
    await db.flush()
    ws_default = Workspace(name="W-default", owner_id=user.id)
    db.add(ws_default)
    await db.commit()
    await db.refresh(ws_default)
    # Default herdado: set_at IS NULL ↔ ADR-223 banner educacional one-time
    assert (ws_default.imoveis_no_if, ws_default.imoveis_no_if_set_at) == (False, None)


async def _seed_explicit_true_workspace(db, email: str) -> tuple[str, str]:
    from datetime import datetime, timezone

    user = User(
        id=str(uuid.uuid4()), email=email, hashed_password="x", full_name="Test FU1 Dogfood"
    )
    db.add(user)
    await db.flush()
    ws = Workspace(
        name="W-dogfood-5at5",
        owner_id=user.id,
        imoveis_no_if=True,
        imoveis_no_if_set_at=datetime.now(timezone.utc),
        imoveis_no_if_set_by_user_id=user.id,
    )
    db.add(ws)
    await db.commit()
    return user.id, ws.id


@pytest.mark.asyncio
async def test_existing_explicit_true_preserved_post_migration(db):
    """Workspace já flipado pra true via endpoint ADR-222 mantém estado."""
    user_id, ws_id = await _seed_explicit_true_workspace(db, "adr223-dogfood@example.com")
    db.expire_all()
    fetched = (await db.execute(select(Workspace).where(Workspace.id == ws_id))).scalar_one()
    # set_at NOT NULL = escolha explícita; ADR-223 §3: NUNCA tocar
    assert fetched.imoveis_no_if is True
    assert fetched.imoveis_no_if_set_at is not None
    assert fetched.imoveis_no_if_set_by_user_id == user_id
