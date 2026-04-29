"""Testes de purge_reports — purge bulk de relatórios + artefatos E5."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.report import Report
from backend.app.models.report_collab import KanbanItem, ReportNotes
from backend.app.services.internal_ops.audit import read_audit
from backend.app.services.internal_ops.purge_reports import purge_reports
from backend.app.services.internal_ops.scope import PurgeScope
from backend.tests.factories import make_report, make_run, make_user, make_workspace


async def _make_artifact(db, *, run, stage: str, key: str) -> PipelineArtifact:
    artifact = PipelineArtifact(
        workspace_id=run.workspace_id,
        pipeline_run_id=run.id,
        stage=stage,
        artifact_key=key,
        content_json={},
    )
    db.add(artifact)
    await db.flush()
    return artifact


async def _add_report_collab(db, *, ws_id: str, report_id: str) -> None:
    db.add(ReportNotes(workspace_id=ws_id, report_id=report_id, content="anotação"))
    db.add(KanbanItem(workspace_id=ws_id, report_id=report_id, titulo="Tarefa", coluna="a_fazer"))
    await db.flush()


@pytest.mark.asyncio
async def test_purge_reports_preview_does_not_delete(db, audit_path: Path) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = await make_run(db, workspace=ws)
    art = await _make_artifact(db, run=run, stage="E5", key="analyze")
    r1 = await make_report(db, workspace=ws, pipeline_run=run, analysis_artifact_id=art.id)
    r2 = await make_report(db, workspace=ws, pipeline_run=run)
    await db.commit()

    result = await purge_reports(
        db, scope=PurgeScope(workspace_id=ws.id), actor="ops1", preview=True
    )
    await db.commit()

    assert result.ok and result.details["preview"] is True
    assert result.details["count"] == 2
    assert set(result.details["ids"]) == {r1.id, r2.id}
    assert result.details["artifacts_to_remove"] == 1
    assert result.details["scope_context"]["owner_email"] == user.email
    assert read_audit(path=audit_path) == []


async def _setup_full_report(db, owner=None) -> tuple[object, int, int]:
    user = owner or await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = await make_run(db, workspace=ws)
    e5 = await _make_artifact(db, run=run, stage="E5", key="analyze")
    e2 = await _make_artifact(db, run=run, stage="E2", key="bank")
    report = await make_report(db, workspace=ws, pipeline_run=run, analysis_artifact_id=e5.id)
    await _add_report_collab(db, ws_id=ws.id, report_id=report.id)
    return ws, e5.id, e2.id


async def _scalars_all(db, stmt):
    return (await db.execute(stmt)).scalars().all()


@pytest.mark.asyncio
async def test_purge_reports_by_workspace_deletes_rows_and_e5(db, audit_path: Path) -> None:
    ws, e5_id, e2_id = await _setup_full_report(db)
    await db.commit()
    result = await purge_reports(
        db, scope=PurgeScope(workspace_id=ws.id), actor="ops1", preview=False
    )
    await db.commit()
    assert result.ok and result.details["count"] == 1
    assert result.details["artifacts_removed"] == 1
    assert await _scalars_all(db, select(Report).where(Report.workspace_id == ws.id)) == []
    assert (
        await _scalars_all(db, select(ReportNotes).where(ReportNotes.workspace_id == ws.id)) == []
    )
    assert await _scalars_all(db, select(KanbanItem).where(KanbanItem.workspace_id == ws.id)) == []
    e5 = await _scalars_all(db, select(PipelineArtifact).where(PipelineArtifact.id == e5_id))
    e2 = await _scalars_all(db, select(PipelineArtifact).where(PipelineArtifact.id == e2_id))
    assert e5 == [] and len(e2) == 1
    assert read_audit(path=audit_path)[0]["action"] == "report.purge"


async def _setup_two_users(db) -> tuple[object, object, object, object]:
    user = await make_user(db)
    ws_a = await make_workspace(db, owner=user, name="WS A")
    ws_b = await make_workspace(db, owner=user, name="WS B")
    ws_other = await make_workspace(db, owner=await make_user(db))
    for w in (ws_a, ws_b, ws_other):
        await make_report(db, workspace=w)
    return user, ws_a, ws_b, ws_other


@pytest.mark.asyncio
async def test_purge_reports_by_user_expands_to_owner_workspaces(db, audit_path: Path) -> None:
    user, ws_a, ws_b, ws_other = await _setup_two_users(db)
    await db.commit()
    result = await purge_reports(db, scope=PurgeScope(user_id=user.id), actor="ops1", preview=False)
    await db.commit()
    assert result.ok and result.details["count"] == 2
    assert set(result.details["scope_context"]["workspace_names"]) == {"WS A", "WS B"}
    user_remaining = await _scalars_all(
        db, select(Report).where(Report.workspace_id.in_([ws_a.id, ws_b.id]))
    )
    other = await _scalars_all(db, select(Report).where(Report.workspace_id == ws_other.id))
    assert user_remaining == [] and len(other) == 1


@pytest.mark.asyncio
async def test_purge_reports_requires_scope(db, audit_path: Path) -> None:
    result = await purge_reports(db, scope=PurgeScope(), actor="ops1", preview=False)
    assert not result.ok and result.error == "scope_required"


@pytest.mark.asyncio
async def test_purge_reports_empty_scope_succeeds(db, audit_path: Path) -> None:
    """Workspace sem reports → count=0, sucesso, audit registrado."""
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await db.commit()

    result = await purge_reports(
        db, scope=PurgeScope(workspace_id=ws.id), actor="ops1", preview=False
    )
    await db.commit()

    assert result.ok and result.details["count"] == 0
    entry = read_audit(path=audit_path)[0]
    assert entry["action"] == "report.purge"
