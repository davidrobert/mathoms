"""Testes do `report_tasks_snapshot_service` (ADR-074 §F8.3)."""

from __future__ import annotations

import pytest

from backend.app.models.report import Report
from backend.app.services.report_tasks_snapshot_service import (
    SNAPSHOT_VERSION,
    build_snapshot,
    get_report_snapshot,
)
from backend.tests import factories


# ─── build_snapshot ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_snapshot_empty_workspace(db):
    ws = await factories.make_workspace(db)
    snapshot = await build_snapshot(ws.id, db=db)
    assert snapshot["version"] == SNAPSHOT_VERSION
    assert snapshot["total"] == 0
    assert snapshot["tasks"] == []
    assert snapshot["counts_by_status"] == {}
    assert "captured_at" in snapshot


@pytest.mark.asyncio
async def test_build_snapshot_includes_all_tasks(db):
    ws = await factories.make_workspace(db)
    await factories.make_task(db, workspace=ws, number=1, priority="S", status="pending")
    await factories.make_task(db, workspace=ws, number=2, priority="R", status="done")
    await factories.make_task(db, workspace=ws, number=3, priority="O", status="cancelled")

    snapshot = await build_snapshot(ws.id, db=db)
    assert snapshot["total"] == 3
    assert snapshot["counts_by_status"] == {"pending": 1, "done": 1, "cancelled": 1}
    assert snapshot["counts_by_priority"] == {"S": 1, "R": 1, "O": 1}
    # Tasks ordenadas por number
    numbers = [t["number"] for t in snapshot["tasks"]]
    assert numbers == [1, 2, 3]


@pytest.mark.asyncio
async def test_build_snapshot_includes_deadline_data(db):
    from datetime import date

    ws = await factories.make_workspace(db)
    await factories.make_task(
        db,
        workspace=ws,
        deadline_kind="HARD_DATE",
        deadline_date=date(2026, 4, 30),
        deadline_label="30/04/2026",
    )
    snapshot = await build_snapshot(ws.id, db=db)
    t = snapshot["tasks"][0]
    assert t["deadline_kind"] == "HARD_DATE"
    assert t["deadline_date"] == "2026-04-30"
    assert t["deadline_label"] == "30/04/2026"


@pytest.mark.asyncio
async def test_build_snapshot_isolated_between_workspaces(db):
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    await factories.make_task(db, workspace=ws_a, title="A-task")
    await factories.make_task(db, workspace=ws_b, title="B-task")

    snap_a = await build_snapshot(ws_a.id, db=db)
    assert snap_a["total"] == 1
    assert snap_a["tasks"][0]["title"] == "A-task"


# ─── get_report_snapshot ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_report_snapshot_returns_stored_json(db):
    ws = await factories.make_workspace(db)
    await factories.make_task(db, workspace=ws, title="Task 1")

    snapshot = await build_snapshot(ws.id, db=db)

    # Cria Report com o snapshot
    report = Report(
        workspace_id=ws.id,
        title="Report teste",
        html_path="/tmp/report.html",
        tasks_snapshot_json=snapshot,
    )
    db.add(report)
    await db.flush()

    result = await get_report_snapshot(ws.id, report.id, db=db)
    assert result is not None
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_get_report_snapshot_returns_none_for_missing_report(db):
    ws = await factories.make_workspace(db)
    result = await get_report_snapshot(
        ws.id, "00000000-0000-0000-0000-000000000000", db=db
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_report_snapshot_cross_tenant_returns_none(db):
    """Report do ws_b não vaza via endpoint de ws_a."""
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    await factories.make_task(db, workspace=ws_b)
    snapshot = await build_snapshot(ws_b.id, db=db)

    report_b = Report(
        workspace_id=ws_b.id,
        title="B's report",
        html_path="/tmp/report.html",
        tasks_snapshot_json=snapshot,
    )
    db.add(report_b)
    await db.flush()

    # ws_a tenta ler report_b.id — deve ser None (não encontrado no escopo)
    result = await get_report_snapshot(ws_a.id, report_b.id, db=db)
    assert result is None


@pytest.mark.asyncio
async def test_get_report_snapshot_returns_null_when_legacy(db):
    """Relatório pré-F8.3 tem tasks_snapshot_json=NULL."""
    ws = await factories.make_workspace(db)
    report = Report(
        workspace_id=ws.id,
        title="Legacy report",
        html_path="/tmp/report.html",
        tasks_snapshot_json=None,
    )
    db.add(report)
    await db.flush()

    result = await get_report_snapshot(ws.id, report.id, db=db)
    assert result is None
