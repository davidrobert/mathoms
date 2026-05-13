"""PlannerReview model tests — persistência + supersedure chain (ADR-199 / ADR-204 / ADR-208, Ato 3)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.planner_review import (
    VALID_PLANNER_REVIEW_STATUSES,
    VALID_TIERS,
    PlannerReview,
)
from backend.tests import factories

SAMPLE_HASH = "a" * 64


async def _make_artifact(db, workspace, run, *, stage: str, key: str) -> PipelineArtifact:
    artifact = PipelineArtifact(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        stage=stage,
        artifact_key=key,
        content_json={"sample": stage},
        schema_version="1.0",
    )
    db.add(artifact)
    await db.flush()
    return artifact


_DEFAULTS = dict(
    status="Gerado",
    persona_hash=SAMPLE_HASH,
    manifest_version="1.0",
    schema_version="1.0",
    model_id="anthropic/claude-sonnet-4.5",
    tier_at_generation="premium",
    items_shown_count=0,
    items_gated_count=0,
    cost_usd_cents=0,
    tokens_in=0,
    tokens_out=0,
    tool_iterations=0,
    latency_ms=0,
)


def _build_review(workspace, run, parecer, e5, **overrides) -> PlannerReview:
    base = dict(_DEFAULTS)
    base.update(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        pipeline_artifact_id=parecer.id,
        e5_artifact_id=e5.id,
    )
    base.update(overrides)
    return PlannerReview(**base)


async def _seed_artifacts(db, *, runs: int = 1):
    workspace = await factories.make_workspace(db)
    run_rows = [await factories.make_run(db, workspace=workspace) for _ in range(runs)]
    e5 = await _make_artifact(db, workspace, run_rows[0], stage="E5", key="analise_financeira")
    parecers = [
        await _make_artifact(db, workspace, r, stage="E6-parecer", key="parecer_planejador")
        for r in run_rows
    ]
    return workspace, run_rows, e5, parecers


async def _fetch_review(db, review_id: str) -> PlannerReview:
    result = await db.execute(select(PlannerReview).where(PlannerReview.id == review_id))
    return result.scalar_one()


@pytest.mark.asyncio
async def test_planner_review_persists_with_minimal_fields(db):
    workspace, (run,), e5, (parecer,) = await _seed_artifacts(db)
    review = _build_review(workspace, run, parecer, e5, cost_usd_cents=20)
    db.add(review)
    await db.flush()

    fetched = await _fetch_review(db, review.id)
    assert fetched.status == "Gerado"
    assert fetched.tier_at_generation == "premium"
    assert fetched.cost_usd_cents == 20
    assert fetched.published_at is None
    assert fetched.superseded_by_id is None


@pytest.mark.asyncio
async def test_unique_workspace_run_constraint(db):
    """Mesmo (workspace, run) com dois pareceres distintos viola UNIQUE."""
    workspace, (run,), e5, (parecer1,) = await _seed_artifacts(db)
    parecer2 = await _make_artifact(
        db, workspace, run, stage="E6-parecer", key="parecer_planejador_v2"
    )

    db.add(_build_review(workspace, run, parecer1, e5))
    await db.flush()
    db.add(_build_review(workspace, run, parecer2, e5))
    with pytest.raises(Exception):
        await db.flush()


@pytest.mark.asyncio
async def test_supersedure_chain_self_fk(db):
    """Aggregate sucessor aponta para antecessor via supersedes_id."""
    workspace, (run1, run2), e5, (parecer1, parecer2) = await _seed_artifacts(db, runs=2)

    parent = _build_review(workspace, run1, parecer1, e5, status="Publicado")
    db.add(parent)
    await db.flush()

    child = _build_review(workspace, run2, parecer2, e5, supersedes_id=parent.id)
    db.add(child)
    await db.flush()

    fetched_child = await _fetch_review(db, child.id)
    assert fetched_child.supersedes_id == parent.id


def test_valid_statuses_enum_contract():
    assert VALID_PLANNER_REVIEW_STATUSES == frozenset(
        {"Pendente", "Gerado", "Publicado", "Superseded"}
    )


def test_valid_tiers_enum_contract():
    assert VALID_TIERS == frozenset({"free", "premium"})
