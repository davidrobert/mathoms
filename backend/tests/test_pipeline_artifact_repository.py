"""Tests — ``backend.app.repositories.pipeline_artifact_repository`` (Fase 2.4)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models import (
    Document,
    DocumentStatus,
    DocumentType,
    PipelineArtifact,
    PipelineRun,
    PipelineRunStatus,
    User,
    Workspace,
)
from backend.app.repositories.pipeline_artifact_repository import (
    PipelineArtifactRepository,
)


async def _seed(db: AsyncSession):
    user = User(email="repo@test.com", hashed_password=hash_password("p"), full_name="R")
    db.add(user)
    await db.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    db.add(ws)
    await db.flush()
    run1 = PipelineRun(workspace_id=ws.id, status=PipelineRunStatus.completed)
    run2 = PipelineRun(workspace_id=ws.id, status=PipelineRunStatus.running)
    db.add_all([run1, run2])
    await db.flush()
    doc = Document(
        workspace_id=ws.id,
        original_name="itau.pdf",
        status=DocumentStatus.ready,
        doc_type=DocumentType.bank_statement,
    )
    db.add(doc)
    await db.flush()
    return ws.id, run1.id, run2.id, doc.id


@pytest.mark.asyncio
async def test_get_latest_for_workspace(db: AsyncSession):
    ws_id, r1, r2, _ = await _seed(db)

    def _do(sync_conn):
        from datetime import datetime, timedelta, timezone

        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            # run1 grava, depois run2 grava (mais recente). created_at explícito:
            # dois defaults datetime.now() no mesmo flush podem empatar no
            # microssegundo e ORDER BY created_at DESC fica arbitrário (flake).
            t0 = datetime.now(timezone.utc)
            s.add(
                PipelineArtifact(
                    workspace_id=ws_id,
                    pipeline_run_id=r1,
                    stage="E5",
                    artifact_key="analise",
                    content_json={"score": 10},
                    created_at=t0,
                )
            )
            s.add(
                PipelineArtifact(
                    workspace_id=ws_id,
                    pipeline_run_id=r2,
                    stage="E5",
                    artifact_key="analise",
                    content_json={"score": 20},
                    created_at=t0 + timedelta(microseconds=1),
                )
            )
            s.commit()
            repo = PipelineArtifactRepository(s)
            latest = repo.get_latest_for_workspace(ws_id, stage="E5")
            return latest.content_json if latest else None

    raw = await db.connection()
    got = await raw.run_sync(_do)
    assert got == {"score": 20}


def _add_e5_artifacts_with_tied_created_at(s, ws_id: str, entries) -> None:
    """Insere artefatos E5 com created_at idêntico — reproduz empate de flush."""
    from datetime import datetime, timezone

    tied = datetime.now(timezone.utc)
    for run_id, content in entries:
        s.add(
            PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=run_id,
                stage="E5",
                artifact_key="analise",
                content_json=content,
                created_at=tied,
            )
        )
    s.commit()


@pytest.mark.asyncio
async def test_get_latest_for_workspace_tiebreak_on_equal_created_at(db: AsyncSession):
    """created_at idêntico → tie-break por id: o último inserido vence sempre."""
    ws_id, r1, r2, _ = await _seed(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            _add_e5_artifacts_with_tied_created_at(
                s, ws_id, [(r1, {"score": 10}), (r2, {"score": 20})]
            )
            repo = PipelineArtifactRepository(s)
            latest = repo.get_latest_for_workspace(ws_id, stage="E5", artifact_key="analise")
            return latest.content_json if latest else None

    raw = await db.connection()
    got = await raw.run_sync(_do)
    assert got == {"score": 20}, "empate em created_at deve resolver pelo maior id (último write)"


@pytest.mark.asyncio
async def test_list_latest_keys(db: AsyncSession):
    ws_id, r1, r2, _ = await _seed(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            for key in ("itau_BRL", "nubank_BRL"):
                s.add(
                    PipelineArtifact(
                        workspace_id=ws_id,
                        pipeline_run_id=r1,
                        stage="E3",
                        artifact_key=key,
                        content_json={},
                    )
                )
            s.commit()
            return PipelineArtifactRepository(s).list_latest_keys(ws_id, stage="E3")

    raw = await db.connection()
    keys = await raw.run_sync(_do)
    assert keys == ["itau_BRL", "nubank_BRL"]


@pytest.mark.asyncio
async def test_get_by_document(db: AsyncSession):
    ws_id, r1, _, doc_id = await _seed(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            s.add(
                PipelineArtifact(
                    workspace_id=ws_id,
                    pipeline_run_id=r1,
                    stage="E2-extratos",
                    artifact_key="itau_202601",
                    document_id=doc_id,
                    content_json={},
                )
            )
            s.add(
                PipelineArtifact(
                    workspace_id=ws_id,
                    pipeline_run_id=r1,
                    stage="E2-extratos",
                    artifact_key="other_202601",
                    document_id=None,
                    content_json={},
                )
            )
            s.commit()
            repo = PipelineArtifactRepository(s)
            artifacts = repo.get_by_document(doc_id, stage="E2-extratos")
            return [a.artifact_key for a in artifacts]

    raw = await db.connection()
    keys = await raw.run_sync(_do)
    assert keys == ["itau_202601"]


@pytest.mark.asyncio
async def test_delete_stage_for_run(db: AsyncSession):
    ws_id, r1, r2, _ = await _seed(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            s.add(
                PipelineArtifact(
                    workspace_id=ws_id,
                    pipeline_run_id=r1,
                    stage="E3",
                    artifact_key="a",
                    content_json={},
                )
            )
            s.add(
                PipelineArtifact(
                    workspace_id=ws_id,
                    pipeline_run_id=r2,
                    stage="E3",
                    artifact_key="a",
                    content_json={},
                )
            )
            s.commit()
            repo = PipelineArtifactRepository(s)
            removed = repo.delete_stage_for_run(r1, stage="E3")
            s.commit()
            remaining = repo.list_latest_keys(ws_id, stage="E3")
            return removed, remaining

    raw = await db.connection()
    removed, remaining = await raw.run_sync(_do)
    assert removed == 1
    assert remaining == ["a"]  # r2 ainda tem


@pytest.mark.asyncio
async def test_delete_stages_for_run(db: AsyncSession):
    ws_id, r1, _, _ = await _seed(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            for stage in ("E3", "E4", "E5"):
                s.add(
                    PipelineArtifact(
                        workspace_id=ws_id,
                        pipeline_run_id=r1,
                        stage=stage,
                        artifact_key="k",
                        content_json={},
                    )
                )
            s.commit()
            repo = PipelineArtifactRepository(s)
            removed = repo.delete_stages_for_run(r1, stages=["E3", "E4"])
            s.commit()
            remaining = s.query(PipelineArtifact).filter_by(pipeline_run_id=r1).count()
            return removed, remaining

    raw = await db.connection()
    removed, remaining = await raw.run_sync(_do)
    assert removed == 2
    assert remaining == 1


@pytest.mark.asyncio
async def test_delete_all_for_workspace(db: AsyncSession):
    ws_id, r1, r2, _ = await _seed(db)

    def _do(sync_conn):
        from sqlalchemy.orm import Session

        with Session(sync_conn) as s:
            s.add(
                PipelineArtifact(
                    workspace_id=ws_id,
                    pipeline_run_id=r1,
                    stage="E3",
                    artifact_key="a",
                    content_json={},
                )
            )
            s.add(
                PipelineArtifact(
                    workspace_id=ws_id,
                    pipeline_run_id=r2,
                    stage="E5",
                    artifact_key="a",
                    content_json={},
                )
            )
            s.commit()
            repo = PipelineArtifactRepository(s)
            removed = repo.delete_all_for_workspace(ws_id)
            s.commit()
            remaining = s.query(PipelineArtifact).count()
            return removed, remaining

    raw = await db.connection()
    removed, remaining = await raw.run_sync(_do)
    assert removed == 2
    assert remaining == 0
