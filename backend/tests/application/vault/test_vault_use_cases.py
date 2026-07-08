"""Use cases ``list_passwords`` / ``create_password`` / ``delete_password``."""

from __future__ import annotations

import pytest

from backend.app.application.base import NotFoundError
from backend.app.application.vault import (
    create_password,
    delete_password,
    list_passwords,
)
from backend.app.schemas.vault import VaultCreateRequest
from backend.app.services.security.vault import get_vault
from backend.tests import factories


@pytest.mark.asyncio
async def test_list_empty_workspace_returns_zero(db):
    ws = await factories.make_workspace(db)
    resp = await list_passwords(ws.id, db=db)
    assert resp.total == 0
    assert resp.passwords == []


@pytest.mark.asyncio
async def test_create_persists_and_omits_raw_password(db):
    ws = await factories.make_workspace(db)
    resp = await create_password(
        ws.id,
        VaultCreateRequest(label="Itaú PDF", password="s3cret"),
        db=db,
        vault=get_vault(),
    )
    assert resp.label == "Itaú PDF"
    assert resp.id


@pytest.mark.asyncio
async def test_list_returns_entries_after_create(db):
    ws = await factories.make_workspace(db)
    for label in ("a", "b"):
        await create_password(
            ws.id,
            VaultCreateRequest(label=label, password="p"),
            db=db,
            vault=get_vault(),
        )
    resp = await list_passwords(ws.id, db=db)
    assert resp.total == 2


@pytest.mark.asyncio
async def test_delete_existing_removes_entry(db):
    ws = await factories.make_workspace(db)
    created = await create_password(
        ws.id,
        VaultCreateRequest(label="temp", password="p"),
        db=db,
        vault=get_vault(),
    )
    await delete_password(ws.id, created.id, db=db)
    resp = await list_passwords(ws.id, db=db)
    assert resp.total == 0


@pytest.mark.asyncio
async def test_delete_missing_raises_not_found(db):
    ws = await factories.make_workspace(db)
    with pytest.raises(NotFoundError):
        await delete_password(ws.id, "none", db=db)
