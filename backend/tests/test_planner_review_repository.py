"""PlannerReviewRepository tests — ADR-199 §D3 (Ato 3 T-12)."""

from __future__ import annotations

import pytest

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.planner_review import PlannerReview
from backend.app.repositories.planner_review_repository import (
    PlannerReviewRepository,
)
from backend.tests import factories

SAMPLE_HASH = "b" * 64


async def _make_artifact(db, workspace, run, *, stage: str, key: str) -> PipelineArtifact:
    artifact = PipelineArtifact(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        stage=stage,
        artifact_key=key,
        content_json={"sample": stage},
    )
    db.add(artifact)
    await db.flush()
    return artifact


def _review_kwargs(workspace, run, parecer, e5, *, status: str) -> dict:
    return dict(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        pipeline_artifact_id=parecer.id,
        e5_artifact_id=e5.id,
        status=status,
        persona_hash=SAMPLE_HASH,
        manifest_version="1.0",
        schema_version="1.0",
        model_id="anthropic/claude-sonnet-4.5",
        tier_at_generation="premium",
        items_shown_count=10,
        items_gated_count=0,
        cost_usd_cents=15,
        tokens_in=5000,
        tokens_out=1000,
        tool_iterations=1,
        latency_ms=8000,
    )


async def _seed_review(db, *, status: str = "Gerado") -> PlannerReview:
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    e5 = await _make_artifact(db, workspace, run, stage="E5", key="analise_financeira")
    parecer = await _make_artifact(db, workspace, run, stage="E6-parecer", key="parecer_planejador")
    review = PlannerReview(**_review_kwargs(workspace, run, parecer, e5, status=status))
    db.add(review)
    await db.flush()
    return review


@pytest.mark.asyncio
async def test_get_by_id_returns_review(db):
    review = await _seed_review(db)
    repo = PlannerReviewRepository(db)

    fetched = await repo.get_by_id(review.workspace_id, review.id)

    assert fetched is not None
    assert fetched.id == review.id
    assert fetched.status == "Gerado"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_other_workspace(db):
    review = await _seed_review(db)
    other_ws = await factories.make_workspace(db)
    repo = PlannerReviewRepository(db)

    fetched = await repo.get_by_id(other_ws.id, review.id)

    assert fetched is None


@pytest.mark.asyncio
async def test_get_latest_for_run(db):
    review = await _seed_review(db)
    repo = PlannerReviewRepository(db)

    fetched = await repo.get_latest_for_run(review.workspace_id, review.pipeline_run_id)

    assert fetched is not None
    assert fetched.id == review.id


@pytest.mark.asyncio
async def test_get_latest_for_workspace_returns_most_recent(db):
    review1 = await _seed_review(db)
    review2 = await _seed_review(db)  # different workspace
    repo = PlannerReviewRepository(db)

    fetched = await repo.get_latest_for_workspace(review1.workspace_id)
    assert fetched is not None
    assert fetched.id == review1.id

    fetched2 = await repo.get_latest_for_workspace(review2.workspace_id)
    assert fetched2 is not None
    assert fetched2.id == review2.id


@pytest.mark.asyncio
async def test_publish_flips_status_and_records_hash(db):
    review = await _seed_review(db)
    repo = PlannerReviewRepository(db)
    hash_value = "c" * 64

    await repo.publish(review.id, immutable_hash=hash_value)
    await db.flush()
    await db.refresh(review)

    assert review.status == "Publicado"
    assert review.immutable_hash == hash_value
    assert review.published_at is not None


@pytest.mark.asyncio
async def test_mark_as_superseded_sets_back_pointer(db):
    parent = await _seed_review(db, status="Publicado")
    successor_id = "01" * 18  # 36 chars
    repo = PlannerReviewRepository(db)

    await repo.mark_as_superseded(parent.id, superseded_by_id=successor_id)
    await db.flush()
    await db.refresh(parent)

    assert parent.status == "Superseded"
    assert parent.superseded_by_id == successor_id
    assert parent.superseded_at is not None


@pytest.mark.asyncio
async def test_list_by_workspace_orders_desc(db):
    review = await _seed_review(db)
    repo = PlannerReviewRepository(db)

    rows = await repo.list_by_workspace(review.workspace_id)

    assert len(rows) == 1
    assert rows[0].id == review.id
