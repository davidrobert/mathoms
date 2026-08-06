"""Healthcheck T-26 — artifact órfão (ADR-199 Ato 6). Cobre query, --fix idempotente, dry-run, idade mínima."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.planner_review import PlannerReview
from backend.scripts.check_orphan_planner_artifacts import (
    _do_fix,
    _find_orphans,
    _retro_create_planner_review,
)
from backend.tests import factories
from backend.tests.helpers.planner_seed import (
    build_e5_artifact,
    build_parecer_artifact,
    build_planner_review,
)


@pytest.fixture
def sync_session() -> Generator[Session, None, None]:
    s = SyncSessionLocal()
    try:
        yield s
    finally:
        s.close()


# `_meta.status` é o que o produtor sempre escreve (_build_artifact_json) e o único
# discriminante de desfecho disponível ao backfill (ADR-366).
_BASE_ARTIFACT_CONTENT = {
    "version": "1.0",
    "metadata": {
        "persona_hash": "f" * 64,
        "manifest_version": "1.0",
        "schema_version": "1.0",
        "model_id": "anthropic/claude-sonnet-4-20250514",
        "tier_at_generation": "premium",
        "generated_at": "2026-05-14T10:00:00+00:00",
    },
    "diagnostico_geral": "diag mínimo para teste de healthcheck órfão",
    "pontos_fortes": [],
    "riscos": [],
    "sugestoes_execucao": [],
    "sugestoes_taticas": [],
    "sugestoes_estrategicas": [],
    "metricas": [],
    "notas_metodologicas": [],
}


def _make_artifact_content(status: str = "Gerado") -> dict:
    return {**_BASE_ARTIFACT_CONTENT, "_meta": {"status": status}}


async def _seed_orphan(db, workspace, age_hours: int = 2, status: str = "Gerado"):
    """Artifact E6-parecer sem PlannerReview correspondente, criado N horas atrás."""
    run = await factories.make_run(db, workspace=workspace)
    e5 = build_e5_artifact(workspace.id, run.id, age_hours=age_hours)
    parecer = build_parecer_artifact(
        workspace.id,
        run.id,
        content_json=_make_artifact_content(status),
        age_hours=age_hours,
    )
    db.add_all([e5, parecer])
    await db.flush()
    return parecer


async def _resolve_e5_id(db, workspace_id: str, run_id: str) -> int:
    """Carrega id do E5 artifact pelo (ws, run)."""
    e5_id = (
        await db.execute(
            select(PipelineArtifact.id).where(
                PipelineArtifact.workspace_id == workspace_id,
                PipelineArtifact.pipeline_run_id == run_id,
                PipelineArtifact.stage == "E5",
            )
        )
    ).scalar_one()
    return e5_id


async def _seed_paired(db, workspace) -> PipelineArtifact:
    """Artifact E6-parecer + PlannerReview correspondente (não-órfão)."""
    parecer = await _seed_orphan(db, workspace, age_hours=2)
    e5_id = await _resolve_e5_id(db, workspace.id, parecer.pipeline_run_id)
    review = build_planner_review(
        workspace.id,
        parecer.pipeline_run_id,
        parecer_artifact_id=parecer.id,
        e5_artifact_id=e5_id,
    )
    db.add(review)
    await db.flush()
    return parecer


@pytest.mark.asyncio
async def test_find_orphans_detects_artifact_without_review(db, sync_session):
    """Artifact > 1h sem PlannerReview → órfão."""
    workspace = await factories.make_workspace(db)
    orphan = await _seed_orphan(db, workspace, age_hours=2)
    await db.commit()

    rows = _find_orphans(sync_session, age_hours=1)
    assert len(rows) == 1
    assert rows[0].artifact_id == orphan.id
    assert rows[0].workspace_id == workspace.id


@pytest.mark.asyncio
async def test_find_orphans_skips_paired_artifact(db, sync_session):
    """Artifact com PlannerReview correspondente NÃO é órfão."""
    workspace = await factories.make_workspace(db)
    await _seed_paired(db, workspace)
    await db.commit()

    rows = _find_orphans(sync_session, age_hours=1)
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_find_orphans_respects_age_hours(db, sync_session):
    """Artifact recente (< age_hours) não é flagged como órfão."""
    workspace = await factories.make_workspace(db)
    await _seed_orphan(db, workspace, age_hours=0)  # criado agora
    await db.commit()

    rows = _find_orphans(sync_session, age_hours=1)
    assert len(rows) == 0  # idade < 1h


@pytest.mark.asyncio
async def test_find_orphans_workspace_filter(db, sync_session):
    """``workspace_id`` filter limita a 1 ws."""
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    await _seed_orphan(db, ws_a, age_hours=2)
    await _seed_orphan(db, ws_b, age_hours=2)
    await db.commit()

    rows = _find_orphans(sync_session, age_hours=1, workspace_id=ws_a.id)
    assert len(rows) == 1
    assert rows[0].workspace_id == ws_a.id


def _reviews_for_artifact(sync_session, artifact_id: int) -> list[PlannerReview]:
    return list(
        sync_session.execute(
            select(PlannerReview).where(PlannerReview.pipeline_artifact_id == artifact_id)
        )
        .scalars()
        .all()
    )


@pytest.mark.asyncio
async def test_fix_creates_retroactive_review(db, sync_session):
    """``--fix`` cria PlannerReview retroativo usando content_json.metadata."""
    workspace = await factories.make_workspace(db)
    orphan_artifact = await _seed_orphan(db, workspace, age_hours=2)
    await db.commit()

    fixed = _do_fix(sync_session, _find_orphans(sync_session, age_hours=1), dry_run=False)
    assert fixed == 1
    reviews = _reviews_for_artifact(sync_session, orphan_artifact.id)
    assert len(reviews) == 1
    assert reviews[0].persona_hash == "f" * 64
    assert reviews[0].workspace_id == workspace.id


@pytest.mark.asyncio
async def test_fix_dry_run_does_not_persist(db, sync_session):
    """``--dry-run`` com ``--fix`` simula mas não comita."""
    workspace = await factories.make_workspace(db)
    await _seed_orphan(db, workspace, age_hours=2)
    await db.commit()

    rows = _find_orphans(sync_session, age_hours=1)
    fixed = _do_fix(sync_session, rows, dry_run=True)
    assert fixed == 1  # contou como "would fix"

    reviews = sync_session.execute(select(PlannerReview)).scalars().all()
    assert len(reviews) == 0  # nada persistido


@pytest.mark.asyncio
async def test_fix_idempotent_when_run_twice(db, sync_session):
    """Segunda execução do fix não duplica (artifact ON, já tem review)."""
    workspace = await factories.make_workspace(db)
    await _seed_orphan(db, workspace, age_hours=2)
    await db.commit()

    rows = _find_orphans(sync_session, age_hours=1)
    _do_fix(sync_session, rows, dry_run=False)

    rows_after = _find_orphans(sync_session, age_hours=1)
    assert len(rows_after) == 0


async def _seed_orphan_parecer_no_e5(db, workspace) -> PipelineArtifact:
    """Cria apenas E6-parecer (sem E5 no mesmo run) — caso de orphan sem lineage."""
    run = await factories.make_run(db, workspace=workspace)
    parecer = build_parecer_artifact(
        workspace.id, run.id, content_json=_make_artifact_content(), age_hours=2
    )
    db.add(parecer)
    await db.flush()
    return parecer


@pytest.mark.asyncio
async def test_retro_create_without_e5_returns_none(db, sync_session):
    """Sem E5 no run → não dá pra criar PlannerReview (FK RESTRICT)."""
    from backend.scripts.check_orphan_planner_artifacts import OrphanRow

    workspace = await factories.make_workspace(db)
    parecer = await _seed_orphan_parecer_no_e5(db, workspace)
    await db.commit()
    orphan = OrphanRow(
        artifact_id=parecer.id,
        workspace_id=workspace.id,
        pipeline_run_id=parecer.pipeline_run_id,
        created_at=parecer.created_at,
    )
    assert _retro_create_planner_review(sync_session, orphan) is None


@pytest.mark.asyncio
async def test_retro_create_skips_artifact_nao_gerado(db, sync_session):
    """Artifact de parecer RETIDO não vira row "Gerado" (ADR-366)."""
    from backend.scripts.check_orphan_planner_artifacts import OrphanRow

    workspace = await factories.make_workspace(db)
    parecer = await _seed_orphan(db, workspace, status="needs_review")
    await db.commit()
    orphan = OrphanRow(
        artifact_id=parecer.id,
        workspace_id=workspace.id,
        pipeline_run_id=parecer.pipeline_run_id,
        created_at=parecer.created_at,
    )
    assert _retro_create_planner_review(sync_session, orphan) is None
