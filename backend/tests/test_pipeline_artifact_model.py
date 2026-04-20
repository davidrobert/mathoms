"""Tests for the PipelineArtifact model — Fase 1.1 do plano de migração.

Verifica:
- CRUD básico no modelo.
- ``UNIQUE(pipeline_run_id, stage, artifact_key)`` é respeitada.
- ``document_id`` FK opcional (preenchido em E2-*, NULL nos demais).
- Content addressable via ``content_json`` (dict arbitrário aceito).
- Índice de listagem ``(workspace_id, stage, artifact_key)`` existe.
- Cascade: delete do ``pipeline_run`` apaga os artefatos; delete do ``document``
  apenas define ``document_id = NULL`` (SET NULL).
"""

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
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


async def _make_workspace_and_run(db: AsyncSession):
    user = User(email="art@test.com", hashed_password=hash_password("p"), full_name="A")
    db.add(user)
    await db.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    db.add(ws)
    await db.flush()
    run = PipelineRun(workspace_id=ws.id, status=PipelineRunStatus.running)
    db.add(run)
    await db.flush()
    return ws.id, run.id


@pytest.mark.asyncio
async def test_pipeline_artifact_crud(db: AsyncSession):
    ws_id, run_id = await _make_workspace_and_run(db)
    art = PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="E2",
        artifact_key="itau_202601",
        content_json={"transactions": [{"v": 1}]},
    )
    db.add(art)
    await db.flush()

    result = await db.execute(
        select(PipelineArtifact).where(PipelineArtifact.workspace_id == ws_id)
    )
    saved = result.scalar_one()
    assert saved.stage == "E2"
    assert saved.artifact_key == "itau_202601"
    assert saved.content_json == {"transactions": [{"v": 1}]}
    assert saved.document_id is None
    assert saved.created_at is not None


@pytest.mark.asyncio
async def test_unique_constraint_run_stage_key(db: AsyncSession):
    ws_id, run_id = await _make_workspace_and_run(db)
    a = PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="E3",
        artifact_key="itau_BRL_202601_202604",
        content_json={},
    )
    db.add(a)
    await db.flush()

    dup = PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="E3",
        artifact_key="itau_BRL_202601_202604",
        content_json={"another": "payload"},
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        await db.flush()


@pytest.mark.asyncio
async def test_same_key_allowed_on_different_stages(db: AsyncSession):
    """Mesma artifact_key em stages distintos é permitido (UNIQUE inclui stage)."""
    ws_id, run_id = await _make_workspace_and_run(db)
    db.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=run_id,
            stage="E2",
            artifact_key="shared_key",
            content_json={},
        )
    )
    db.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=run_id,
            stage="E3",
            artifact_key="shared_key",
            content_json={},
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_document_fk_declares_set_null(db: AsyncSession):
    """Verifica no schema que ``document_id`` declara ``ON DELETE SET NULL``.

    Nota: SQLite não força FK por default — o comportamento em runtime é
    testado contra Postgres (produção). Aqui validamos apenas a declaração.
    """

    def _check(sync_conn):
        insp = inspect(sync_conn)
        fks = insp.get_foreign_keys("pipeline_artifacts")
        doc_fk = next(
            (fk for fk in fks if fk["referred_table"] == "documents"), None
        )
        assert doc_fk is not None, "FK para documents não encontrada"
        options = doc_fk.get("options") or {}
        assert options.get("ondelete", "").upper() == "SET NULL"

    raw = await db.connection()
    await raw.run_sync(_check)


@pytest.mark.asyncio
async def test_pipeline_run_fk_declares_cascade(db: AsyncSession):
    """Verifica no schema que ``pipeline_run_id`` declara ``ON DELETE CASCADE``."""

    def _check(sync_conn):
        insp = inspect(sync_conn)
        fks = insp.get_foreign_keys("pipeline_artifacts")
        run_fk = next(
            (fk for fk in fks if fk["referred_table"] == "pipeline_runs"), None
        )
        assert run_fk is not None
        options = run_fk.get("options") or {}
        assert options.get("ondelete", "").upper() == "CASCADE"

    raw = await db.connection()
    await raw.run_sync(_check)


@pytest.mark.asyncio
async def test_indexes_are_created(db: AsyncSession):
    """Sanidade: índices declarados no modelo existem na tabela."""

    def _collect(sync_conn):
        insp = inspect(sync_conn)
        return {ix["name"] for ix in insp.get_indexes("pipeline_artifacts")}

    raw = await db.connection()
    names = await raw.run_sync(_collect)
    expected = {
        "ix_pipeline_artifacts_workspace_id",
        "ix_pipeline_artifacts_workspace_stage_key",
        "ix_pipeline_artifacts_document_id",
    }
    missing = expected - names
    assert not missing, f"Índices faltando: {missing}"
