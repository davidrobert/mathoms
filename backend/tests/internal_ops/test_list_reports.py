"""Testes de list_reports."""

from __future__ import annotations

import pytest

from backend.app.models.report import Report
from backend.app.services.internal_ops.list_reports import (
    ListReportsFilter,
    list_reports,
)
from backend.tests.factories import make_user, make_workspace


async def _make_report(db, *, workspace, title: str) -> Report:
    r = Report(
        workspace_id=workspace.id,
        title=title,
    )
    db.add(r)
    await db.flush()
    return r


@pytest.mark.asyncio
async def test_list_reports_by_workspace(db) -> None:
    u = await make_user(db)
    ws = await make_workspace(db, owner=u)
    await _make_report(db, workspace=ws, title="R1")
    await _make_report(db, workspace=ws, title="R2")
    await db.commit()

    out, total = await list_reports(db, filter=ListReportsFilter(workspace_id=ws.id))
    assert {r.title for r in out} == {"R1", "R2"}
    assert total == 2


@pytest.mark.asyncio
async def test_list_reports_by_user(db) -> None:
    u1 = await make_user(db)
    u2 = await make_user(db)
    ws1 = await make_workspace(db, owner=u1)
    ws2 = await make_workspace(db, owner=u2)
    await _make_report(db, workspace=ws1, title="forU1")
    await _make_report(db, workspace=ws2, title="forU2")
    await db.commit()

    out, total = await list_reports(db, filter=ListReportsFilter(user_id=u1.id))
    assert [r.title for r in out] == ["forU1"]
    assert total == 1


@pytest.mark.asyncio
async def test_list_reports_pagination(db) -> None:
    u = await make_user(db)
    ws = await make_workspace(db, owner=u)
    for i in range(5):
        await _make_report(db, workspace=ws, title=f"R{i}")
    await db.commit()

    page1, total = await list_reports(
        db, filter=ListReportsFilter(workspace_id=ws.id, limit=2, offset=0)
    )
    page2, _ = await list_reports(
        db, filter=ListReportsFilter(workspace_id=ws.id, limit=2, offset=2)
    )
    assert total == 5
    assert len(page1) == 2 and len(page2) == 2
    assert {r.id for r in page1}.isdisjoint({r.id for r in page2})
