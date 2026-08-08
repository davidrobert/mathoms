"""Testes de reset_workspace_from_stage (ADR-212 PR1b)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.services.internal_ops.audit import read_audit
from backend.app.services.internal_ops.pipeline_reset import (
    reset_workspace_from_stage,
)
from backend.tests.factories import make_report, make_run, make_user, make_workspace


async def _make_artifact(db, *, run, stage: str, key: str) -> PipelineArtifact:
    artifact = PipelineArtifact(
        workspace_id=run.workspace_id,
        pipeline_run_id=run.id,
        stage=stage,
        artifact_key=key,
        content_json={"foo": "bar"},
    )
    db.add(artifact)
    await db.flush()
    return artifact


async def _scalars_all(db, stmt):
    return (await db.execute(stmt)).scalars().all()


async def _seed_pipeline_artifacts(db, ws) -> dict[str, int]:
    """Cria 1 artefato por stage canónico relevante. Retorna {stage: artifact_id}."""
    run = await make_run(db, workspace=ws)
    stages = [
        "route_documents",
        "extract_statements",
        "reconcile_transactions",
        "categorize_transactions",
        "analyze_finances",
        "validate_cross",
    ]
    out: dict[str, int] = {}
    for stage in stages:
        art = await _make_artifact(db, run=run, stage=stage, key=f"key_{stage}")
        out[stage] = art.id
    return out


@pytest.mark.asyncio
async def test_reset_preview_does_not_delete(db) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    ids_by_stage = await _seed_pipeline_artifacts(db, ws)
    await db.commit()

    result = await reset_workspace_from_stage(
        db,
        workspace_id=ws.id,
        from_stage="reconcile_transactions",
        actor="ops1",
        preview=True,
    )
    await db.commit()

    assert result.ok and result.details["preview"] is True
    # 4 stages a partir de reconcile_transactions (inclui): reconcile,
    # categorize, analyze, generate_narratives (sem artifact), validate_cross,
    # review_finances_holistic (sem artifact). Apenas 4 desses têm artefatos.
    assert result.details["artifacts_affected"] == 4
    assert result.details["from_stage"] == "reconcile_transactions"
    assert "reconcile_transactions" in result.details["stages_affected"]
    assert "validate_cross" in result.details["stages_affected"]
    # Stages anteriores não aparecem
    assert "extract_statements" not in result.details["stages_affected"]

    # Nenhum delete; counts intactos
    remaining = await _scalars_all(
        db, select(PipelineArtifact).where(PipelineArtifact.workspace_id == ws.id)
    )
    assert len(remaining) == len(ids_by_stage)
    # Audit não registrado em preview
    assert await read_audit(db) == []


@pytest.mark.asyncio
async def test_reset_from_middle_deletes_only_cascade(db) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    ids_by_stage = await _seed_pipeline_artifacts(db, ws)
    await db.commit()

    result = await reset_workspace_from_stage(
        db,
        workspace_id=ws.id,
        from_stage="categorize_transactions",
        actor="ops1",
        preview=False,
    )
    await db.commit()

    assert result.ok and result.details["preview"] is False
    # 3 stages com artefato a partir de categorize: categorize, analyze, validate_cross
    assert result.details["artifacts_deleted"] == 3

    remaining_stages = {
        r.stage
        for r in await _scalars_all(
            db, select(PipelineArtifact).where(PipelineArtifact.workspace_id == ws.id)
        )
    }
    # Stages anteriores preservadas
    assert remaining_stages == {
        "route_documents",
        "extract_statements",
        "reconcile_transactions",
    }
    # IDs antes de cascade ainda existem
    for stage_kept in remaining_stages:
        assert ids_by_stage[stage_kept] is not None


@pytest.mark.asyncio
async def test_reset_from_first_stage_deletes_all(db) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await _seed_pipeline_artifacts(db, ws)
    await db.commit()

    result = await reset_workspace_from_stage(
        db,
        workspace_id=ws.id,
        from_stage="unlock_documents",
        actor="ops1",
        preview=False,
    )
    await db.commit()

    assert result.ok and result.details["artifacts_deleted"] == 6
    remaining = await _scalars_all(
        db, select(PipelineArtifact).where(PipelineArtifact.workspace_id == ws.id)
    )
    assert remaining == []


@pytest.mark.asyncio
async def test_legacy_stage_name_resolves_to_descriptive(db) -> None:
    """Stage legacy "E3" deve resolver para "reconcile_transactions" via STAGE_RENAME_MAP."""
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await _seed_pipeline_artifacts(db, ws)
    await db.commit()

    result = await reset_workspace_from_stage(
        db,
        workspace_id=ws.id,
        from_stage="E3",  # legacy
        actor="ops1",
        preview=True,
    )

    assert result.ok
    assert result.details["from_stage"] == "reconcile_transactions"


@pytest.mark.asyncio
async def test_reset_matches_legacy_stage_rows_in_db(db) -> None:
    """DB com row em formato legacy ("E3") é deletado quando cascade inclui."""
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = await make_run(db, workspace=ws)
    art_legacy = await _make_artifact(db, run=run, stage="E3", key="legacy_e3")
    art_descriptive = await _make_artifact(
        db, run=run, stage="categorize_transactions", key="new_e4"
    )
    await db.commit()

    result = await reset_workspace_from_stage(
        db,
        workspace_id=ws.id,
        from_stage="reconcile_transactions",
        actor="ops1",
        preview=False,
    )
    await db.commit()

    assert result.ok and result.details["artifacts_deleted"] == 2
    remaining = await _scalars_all(
        db, select(PipelineArtifact).where(PipelineArtifact.workspace_id == ws.id)
    )
    assert remaining == []
    assert art_legacy.id is not None and art_descriptive.id is not None  # not None pre-delete


async def _ws_com_relatorio_antigo(db):
    """Workspace com E5 referenciado por report + 1 artefato solto no cascade."""
    ws = await make_workspace(db, owner=await make_user(db))
    run = await make_run(db, workspace=ws)
    e5 = await _make_artifact(db, run=run, stage="analyze_finances", key="analise_financeira")
    solto = await _make_artifact(db, run=run, stage="reconcile_transactions", key="itau")
    report = await make_report(db, workspace=ws, pipeline_run=run, analysis_artifact_id=e5.id)
    await db.commit()
    return ws, e5, solto, report


async def _ids_vivos(db, ws_id: str) -> set[int]:
    stmt = select(PipelineArtifact).where(PipelineArtifact.workspace_id == ws_id)
    return {r.id for r in await _scalars_all(db, stmt)}


# Antes da guarda, reset a partir de `extract_baseline` apagava o E5 de **todos**
# os runs históricos — em Postgres o `SET NULL` deixava o relatório antigo sem
# análise (404 em `/reports/{id}/data`): perda de dado por ação de operador.
@pytest.mark.asyncio
async def test_reset_preserves_artifact_referenced_by_report(db) -> None:
    """ADR-371: o E5 de um relatório antigo sobrevive ao reset do workspace."""
    ws, e5, solto, report = await _ws_com_relatorio_antigo(db)

    result = await reset_workspace_from_stage(
        db, workspace_id=ws.id, from_stage="reconcile_transactions", actor="ops1", preview=False
    )
    await db.commit()

    assert result.details["artifacts_deleted"] == 1  # só o `solto`
    assert result.details["artifacts_preserved_referenced"] == 1
    vivos = await _ids_vivos(db, ws.id)
    assert e5.id in vivos and solto.id not in vivos
    await db.refresh(report)
    assert report.analysis_artifact_id == e5.id


@pytest.mark.asyncio
async def test_reset_preview_conta_preservados(db) -> None:
    """A preview precisa dizer o que vai preservar — reset que preserva sem
    avisar é a mesma classe de erro do purge que apaga sem avisar."""
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = await make_run(db, workspace=ws)
    e5 = await _make_artifact(db, run=run, stage="analyze_finances", key="analise_financeira")
    await make_report(db, workspace=ws, pipeline_run=run, analysis_artifact_id=e5.id)
    await db.commit()

    result = await reset_workspace_from_stage(
        db, workspace_id=ws.id, from_stage="analyze_finances", actor="ops1", preview=True
    )

    assert result.ok
    assert result.details["artifacts_affected"] == 0
    assert result.details["artifacts_preserved_referenced"] == 1


@pytest.mark.asyncio
async def test_workspace_not_found(db) -> None:
    result = await reset_workspace_from_stage(
        db,
        workspace_id="00000000-0000-0000-0000-000000000000",
        from_stage="reconcile_transactions",
        actor="ops1",
        preview=False,
    )
    assert not result.ok and result.error == "workspace_not_found"


@pytest.mark.asyncio
async def test_unknown_stage(db) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await db.commit()

    result = await reset_workspace_from_stage(
        db,
        workspace_id=ws.id,
        from_stage="not_a_real_stage",
        actor="ops1",
        preview=False,
    )
    assert not result.ok and result.error == "unknown_stage"
    assert "valid_stages" in result.details


@pytest.mark.asyncio
async def test_empty_workspace_returns_zero(db) -> None:
    """Workspace sem artefatos → artifacts_affected=0, sucesso."""
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await db.commit()

    result = await reset_workspace_from_stage(
        db,
        workspace_id=ws.id,
        from_stage="unlock_documents",
        actor="ops1",
        preview=False,
    )
    await db.commit()

    assert result.ok and result.details["artifacts_deleted"] == 0


@pytest.mark.asyncio
async def test_audit_registered_when_not_preview(db) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await _seed_pipeline_artifacts(db, ws)
    await db.commit()

    await reset_workspace_from_stage(
        db,
        workspace_id=ws.id,
        from_stage="analyze_finances",
        actor="ops1",
        preview=False,
    )
    await db.commit()

    entries = await read_audit(db)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["action"] == "pipeline.reset_from_stage"
    assert entry["actor"] == "ops1"
    assert entry["target_id"] == ws.id
    assert entry["details"]["from_stage"] == "analyze_finances"
    assert entry["details"]["artifacts_deleted"] >= 1
