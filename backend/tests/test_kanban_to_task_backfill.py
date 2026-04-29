"""Parity tests do backfill ADR-153 (kanban→tasks + report_notes→workspace_notes, idempotente)."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from backend.app.models.report_collab import KanbanItem, ReportNotes
from backend.app.models.task import Task
from backend.app.models.workspace_note import WorkspaceNotes
from backend.tests import factories
from dev.migrate_kanban_to_task import migrate_workspace as _raw_migrate_workspace


async def _make_report(db, workspace):
    from backend.app.models.report import Report

    rpt = Report(
        workspace_id=workspace.id,
        title="r",
        period="2026-04",
        created_at=datetime.now(timezone.utc),
    )
    db.add(rpt)
    await db.flush()
    return rpt


def _kanban(ws_id, report_id, **overrides):
    base = dict(
        workspace_id=ws_id,
        report_id=report_id,
        titulo="t",
        coluna="a_fazer",
        categoria="Invest",
        essencial="R",
    )
    base.update(overrides)
    return KanbanItem(**base)


async def _seed(db, *, kanban=(), notes=()):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    rpt = await _make_report(db, ws)
    for k in kanban:
        db.add(_kanban(ws.id, rpt.id, **k))
    for n in notes:
        note_rpt = await _make_report(db, ws)
        db.add(ReportNotes(workspace_id=ws.id, report_id=note_rpt.id, **n))
    await db.commit()
    return ws, rpt


async def _all_migrated_tasks(db, ws_id):
    result = await db.execute(
        select(Task).where(Task.workspace_id == ws_id, Task.created_from == "kanban_migration")
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_backfill_creates_tasks_from_kanban(db):
    ws, rpt = await _seed(
        db,
        kanban=[
            dict(
                titulo="Quitar",
                coluna="em_andamento",
                prioridade="alta",
                prazo=date(2026, 6, 30),
                categoria="Orcamento",
                essencial="S",
                ordem=1,
            ),
            dict(titulo="PGBL", coluna="a_fazer", categoria="Tributario", essencial="R", ordem=2),
        ],
    )
    stats = await _raw_migrate_workspace(ws.id, dry_run=False, session=db)
    assert (stats.kanban_items_seen, stats.tasks_created, stats.tasks_skipped) == (2, 2, 0)
    by_title = {t.title: t for t in await _all_migrated_tasks(db, ws.id)}
    quitar = by_title["Quitar"]
    assert (quitar.status, quitar.urgency, quitar.priority) == ("in_progress", "alta", "S")
    assert (quitar.board_column, quitar.board_order, quitar.is_board_only) == (
        "em_andamento",
        1,
        True,
    )
    assert (quitar.deadline_kind, quitar.deadline_date) == ("HARD_DATE", date(2026, 6, 30))
    assert quitar.origin_report_id == rpt.id
    pgbl = by_title["PGBL"]
    assert (pgbl.status, pgbl.urgency, pgbl.deadline_kind) == ("pending", None, "UNSCHEDULED")


@pytest.mark.asyncio
async def test_backfill_is_idempotent(db):
    ws, _ = await _seed(db, kanban=[dict(titulo="única")])
    s1 = await _raw_migrate_workspace(ws.id, dry_run=False, session=db)
    s2 = await _raw_migrate_workspace(ws.id, dry_run=False, session=db)
    assert (s1.tasks_created, s1.tasks_skipped) == (1, 0)
    assert (s2.tasks_created, s2.tasks_skipped) == (0, 1)
    assert len(await _all_migrated_tasks(db, ws.id)) == 1


@pytest.mark.asyncio
async def test_backfill_concatenates_report_notes(db):
    ws, _ = await _seed(
        db,
        notes=[dict(content="Primeira."), dict(content="Segunda.")],
    )
    stats = await _raw_migrate_workspace(ws.id, dry_run=False, session=db)
    assert (stats.report_notes_seen, stats.workspace_notes_created) == (2, 1)
    result = await db.execute(select(WorkspaceNotes).where(WorkspaceNotes.workspace_id == ws.id))
    notes = list(result.scalars().all())
    assert len(notes) == 1
    note = notes[0]
    assert (note.title, note.pinned) == ("Notas migradas do relatório", True)
    assert "Primeira." in note.content and "Segunda." in note.content


@pytest.mark.asyncio
async def test_backfill_skips_already_migrated_notes(db):
    ws, _ = await _seed(db, notes=[dict(content="x")])
    s1 = await _raw_migrate_workspace(ws.id, dry_run=False, session=db)
    s2 = await _raw_migrate_workspace(ws.id, dry_run=False, session=db)
    assert (s1.workspace_notes_created, s2.workspace_notes_created, s2.workspace_notes_skipped) == (
        1,
        0,
        1,
    )


@pytest.mark.asyncio
async def test_backfill_dry_run_changes_nothing(db):
    ws, _ = await _seed(db, kanban=[dict(titulo="dry")])
    stats = await _raw_migrate_workspace(ws.id, dry_run=True, session=db)
    assert stats.tasks_created == 1
    assert await _all_migrated_tasks(db, ws.id) == []


@pytest.mark.asyncio
async def test_backfill_empty_workspace_is_noop(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    stats = await _raw_migrate_workspace(ws.id, dry_run=False, session=db)
    assert (stats.kanban_items_seen, stats.tasks_created) == (0, 0)
    assert (stats.report_notes_seen, stats.workspace_notes_created) == (0, 0)
