"""Testes de delete_document e purge_documents."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.models.document import Document
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun
from backend.app.services.internal_ops.audit import read_audit
from backend.app.services.internal_ops.delete_document import delete_document
from backend.app.services.internal_ops.purge_documents import (
    PurgeScope,
    purge_documents,
)
from backend.tests.factories import (
    make_document,
    make_run,
    make_user,
    make_workspace,
)


@pytest.mark.asyncio
async def test_delete_document_removes_row_and_blob(
    db, audit_path: Path, tmp_path: Path, monkeypatch
) -> None:
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "STORAGE_ROOT", tmp_path)

    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    blob_rel = "inbox/x.pdf"
    blob_abs = tmp_path / ws.id / blob_rel
    blob_abs.parent.mkdir(parents=True, exist_ok=True)
    blob_abs.write_bytes(b"content")

    doc = await make_document(db, workspace=ws, stored_path=blob_rel)
    await db.commit()

    result = await delete_document(db, doc.id, actor="ops1")
    await db.commit()

    assert result.ok and result.details["blob_removed"] is True
    assert not blob_abs.exists()
    assert (
        await db.execute(select(Document).where(Document.id == doc.id))
    ).scalar_one_or_none() is None

    entry = read_audit(path=audit_path)[0]
    assert entry["action"] == "document.delete"
    assert entry["details"]["content_hash"] == doc.content_hash
    assert entry["details"]["original_name"] == doc.original_name
    assert entry["details"]["blob_removed"] is True


@pytest.mark.asyncio
async def test_delete_document_missing(db, audit_path: Path) -> None:
    result = await delete_document(db, "nope", actor="ops1")
    assert not result.ok and result.error == "document_not_found"


@pytest.mark.asyncio
async def test_purge_preview_does_not_delete(db, audit_path: Path) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    d1 = await make_document(db, workspace=ws)
    d2 = await make_document(db, workspace=ws)
    await db.commit()

    result = await purge_documents(
        db, scope=PurgeScope(workspace_id=ws.id), actor="ops1", preview=True
    )
    await db.commit()

    assert result.ok and result.details["preview"] is True
    assert result.details["count"] == 2
    assert set(result.details["ids"]) == {d1.id, d2.id}
    assert result.details["scope_context"]["owner_email"] == user.email
    assert result.details["scope_context"]["workspace_names"] == [ws.name]
    assert read_audit(path=audit_path) == []


async def _setup_doc_with_artifact(db) -> object:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await make_document(db, workspace=ws)
    run = await make_run(db, workspace=ws)
    db.add(
        PipelineArtifact(
            workspace_id=ws.id,
            pipeline_run_id=run.id,
            stage="E2",
            artifact_key="bank",
            content_json={"transactions": []},
        )
    )
    return ws


@pytest.mark.asyncio
async def test_purge_cascades_pipeline_runs_and_artifacts(db, audit_path: Path) -> None:
    """Purge de docs limpa pipeline_runs do escopo (cascade pega artefatos)."""
    ws = await _setup_doc_with_artifact(db)
    await db.commit()
    result = await purge_documents(
        db, scope=PurgeScope(workspace_id=ws.id), actor="ops1", preview=False
    )
    await db.commit()
    assert result.ok and result.details["runs_removed"] == 1
    runs = (
        (await db.execute(select(PipelineRun).where(PipelineRun.workspace_id == ws.id)))
        .scalars()
        .all()
    )
    arts = (
        (await db.execute(select(PipelineArtifact).where(PipelineArtifact.workspace_id == ws.id)))
        .scalars()
        .all()
    )
    assert runs == [] and arts == []


@pytest.mark.asyncio
async def test_purge_confirm_by_user(db, audit_path: Path) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await make_document(db, workspace=ws)
    await make_document(db, workspace=ws)
    await db.commit()

    result = await purge_documents(
        db, scope=PurgeScope(user_id=user.id), actor="ops1", preview=False
    )
    await db.commit()

    assert result.ok and result.details["count"] == 2
    remaining = (
        (await db.execute(select(Document).where(Document.workspace_id == ws.id))).scalars().all()
    )
    assert remaining == []

    entry = read_audit(path=audit_path)[0]
    assert entry["action"] == "document.purge"


@pytest.mark.asyncio
async def test_purge_requires_scope(db, audit_path: Path) -> None:
    result = await purge_documents(db, scope=PurgeScope(), actor="ops1", preview=False)
    assert not result.ok and result.error == "scope_required"


@pytest.mark.asyncio
async def test_purge_rollback_on_blob_failure(
    db, audit_path: Path, tmp_path: Path, monkeypatch
) -> None:
    """S3.c — se `unlink` lançar OSError, DB rollback mantém rows intactos."""
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "STORAGE_ROOT", tmp_path)

    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    d1 = await make_document(db, workspace=ws, stored_path="a.pdf")
    d2 = await make_document(db, workspace=ws, stored_path="b.pdf")
    d1_id, d2_id, ws_id = d1.id, d2.id, ws.id
    for rel in ("a.pdf", "b.pdf"):
        p = tmp_path / ws_id / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    await db.commit()

    original_unlink = Path.unlink

    def _flaky_unlink(self, *args, **kwargs):
        if self.name == "b.pdf":
            raise OSError("permission denied")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _flaky_unlink)

    result = await purge_documents(
        db, scope=PurgeScope(workspace_id=ws_id), actor="ops1", preview=False
    )

    assert not result.ok and result.error == "partial_failure"
    assert d2_id in result.details["failed_blobs"]
    remaining = set(
        (await db.execute(select(Document.id).where(Document.workspace_id == ws_id)))
        .scalars()
        .all()
    )
    assert remaining == {d1_id, d2_id}
