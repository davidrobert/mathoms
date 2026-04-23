"""Testes do metrics snapshot."""

from __future__ import annotations

import pytest

from backend.app.services.internal_ops.metrics import get_metrics
from backend.tests.factories import make_document, make_user, make_workspace


@pytest.mark.asyncio
async def test_metrics_empty(db) -> None:
    snap = await get_metrics(db)
    assert snap.users_total == 0
    assert snap.workspaces_total == 0
    assert snap.storage_bytes_total == 0


@pytest.mark.asyncio
async def test_metrics_counts(db) -> None:
    u1 = await make_user(db)
    u2 = await make_user(db, is_active=False)
    ws = await make_workspace(db, owner=u1)
    await make_document(db, workspace=ws, file_size_bytes=1000)
    await make_document(db, workspace=ws, file_size_bytes=2500)
    await db.commit()

    snap = await get_metrics(db)
    assert snap.users_total == 2
    assert snap.users_active == 1
    assert snap.workspaces_total == 1
    assert snap.documents_total == 2
    assert snap.storage_bytes_total == 3500
