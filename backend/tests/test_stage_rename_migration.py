"""Tests — ``q5r6s7t8u9v0_rename_stage_identifiers`` (Fase 9.3 · ADR-093).

Valida a função ``apply_rename(bind, mapping)`` sem invocar o CLI do alembic.
Cobre:
- ``upgrade`` renomeia todas as linhas com nomes legados.
- ``downgrade`` restaura os nomes legados (reversibilidade).
- Idempotência: rodar ``upgrade`` duas vezes não duplica/corrompe.
- Tabela vazia é no-op válido.
- Colunas não-``stage`` ficam intactas.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models import (
    PipelineArtifact,
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
    User,
    Workspace,
)

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "q5r6s7t8u9v0_rename_stage_identifiers.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("q5r6s7t8u9v0_rename", MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


async def _seed_ws_and_run(db: AsyncSession, *, email: str):
    user = User(email=email, hashed_password=hash_password("p"), full_name="M")
    db.add(user)
    await db.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    db.add(ws)
    await db.flush()
    run = PipelineRun(workspace_id=ws.id, status=PipelineRunStatus.completed)
    db.add(run)
    await db.flush()
    return ws.id, run.id


@pytest.mark.asyncio
async def test_upgrade_renames_all_known_stages(db: AsyncSession):
    mod = _load_migration()
    ws_id, run_id = await _seed_ws_and_run(db, email="mig1@test.com")

    for i, old in enumerate(mod.STAGE_RENAME):
        db.add(
            PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=run_id,
                stage=old,
                artifact_key=f"k{i}",
                content_json={"i": i},
            )
        )
        if old != "E5-revised":
            db.add(
                PipelineStageLog(
                    pipeline_run_id=run_id,
                    stage=old,
                    status=PipelineStageStatus.completed,
                )
            )
    await db.commit()

    def _apply(sync_conn):
        mod.apply_rename(sync_conn, mod.STAGE_RENAME)

    raw = await db.connection()
    await raw.run_sync(_apply)

    for old, new in mod.STAGE_RENAME.items():
        rows_old = (
            (await db.execute(select(PipelineArtifact).where(PipelineArtifact.stage == old)))
            .scalars()
            .all()
        )
        assert rows_old == [], f"Sobrevivente '{old}'"
        rows_new = (
            (await db.execute(select(PipelineArtifact).where(PipelineArtifact.stage == new)))
            .scalars()
            .all()
        )
        assert len(rows_new) == 1


@pytest.mark.asyncio
async def test_downgrade_restores_legacy_names(db: AsyncSession):
    mod = _load_migration()
    ws_id, run_id = await _seed_ws_and_run(db, email="mig2@test.com")

    for i, (old, new) in enumerate(mod.STAGE_RENAME.items()):
        db.add(
            PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=run_id,
                stage=new,
                artifact_key=f"k{i}",
                content_json={},
            )
        )
    await db.commit()

    def _apply(sync_conn):
        reverse = {new: old for old, new in mod.STAGE_RENAME.items()}
        mod.apply_rename(sync_conn, reverse)

    raw = await db.connection()
    await raw.run_sync(_apply)

    for old, new in mod.STAGE_RENAME.items():
        rows_new = (
            (await db.execute(select(PipelineArtifact).where(PipelineArtifact.stage == new)))
            .scalars()
            .all()
        )
        assert rows_new == []
        rows_old = (
            (await db.execute(select(PipelineArtifact).where(PipelineArtifact.stage == old)))
            .scalars()
            .all()
        )
        assert len(rows_old) == 1


@pytest.mark.asyncio
async def test_migration_is_idempotent(db: AsyncSession):
    mod = _load_migration()
    ws_id, run_id = await _seed_ws_and_run(db, email="mig3@test.com")
    db.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=run_id,
            stage="E3",
            artifact_key="k",
            content_json={},
        )
    )
    await db.commit()

    def _apply(sync_conn):
        mod.apply_rename(sync_conn, mod.STAGE_RENAME)

    raw = await db.connection()
    await raw.run_sync(_apply)
    await raw.run_sync(_apply)

    rows = (await db.execute(select(PipelineArtifact))).scalars().all()
    assert len(rows) == 1
    assert rows[0].stage == "reconcile_transactions"


@pytest.mark.asyncio
async def test_migration_handles_empty_table(db: AsyncSession):
    mod = _load_migration()

    def _apply(sync_conn):
        mod.apply_rename(sync_conn, mod.STAGE_RENAME)

    raw = await db.connection()
    await raw.run_sync(_apply)

    rows = (await db.execute(select(PipelineArtifact))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_migration_preserves_non_stage_columns(db: AsyncSession):
    mod = _load_migration()
    ws_id, run_id = await _seed_ws_and_run(db, email="mig5@test.com")
    db.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=run_id,
            stage="E5",
            artifact_key="analise",
            content_json={"score": 82, "detail": [1, 2, 3]},
            schema_version="v1",
            byte_size=1234,
        )
    )
    await db.commit()

    def _apply(sync_conn):
        mod.apply_rename(sync_conn, mod.STAGE_RENAME)

    raw = await db.connection()
    await raw.run_sync(_apply)

    row = (await db.execute(select(PipelineArtifact))).scalar_one()
    assert row.stage == "analyze_finances"
    assert row.artifact_key == "analise"
    assert row.content_json == {"score": 82, "detail": [1, 2, 3]}
    assert row.schema_version == "v1"
    assert row.byte_size == 1234
