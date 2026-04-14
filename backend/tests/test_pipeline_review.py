"""Tests for Phase 4D: tier detection, needs_review workflow, resume, stage reviews."""

from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.llm_config import LLMConfig
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.models.workspace import Workspace
from backend.app.services.vault import VaultService


_vault = VaultService()
_START = "backend.app.api.pipeline.start_pipeline_run"


async def _setup_workspace_with_llm(db: AsyncSession, client: AsyncClient) -> tuple[str, str]:
    """Register user, get workspace, add LLM config. Returns (ws_id, token)."""
    resp = await client.post("/api/auth/register", json={
        "email": "review@test.com",
        "password": "testpass123",
        "full_name": "Review Tester",
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    result = await db.execute(select(Workspace))
    ws = result.scalar_one()

    llm_cfg = LLMConfig(
        workspace_id=ws.id,
        provider="anthropic",
        api_key_encrypted=_vault.encrypt("sk-test-fake"),
        model_name="claude-sonnet-4-20250514",
    )
    db.add(llm_cfg)
    await db.commit()

    return ws.id, token


async def _create_needs_review_run(db: AsyncSession, ws_id: str) -> tuple[str, str]:
    """Create a PipelineRun in needs_review state with a pending StageReview."""
    run = PipelineRun(
        workspace_id=ws_id,
        status=PipelineRunStatus.needs_review,
        tier_at_run="premium",
        paused_at_stage="E1",
    )
    db.add(run)
    await db.flush()

    review = StageReview(
        pipeline_run_id=run.id,
        stage="E1",
        status=StageReviewStatus.pending,
        original_output_json={"members_extracted": 1, "validation": {"valid": False, "errors": ["test error"]}},
        validation_errors="test error",
    )
    db.add(review)
    await db.commit()

    return run.id, review.id


# ── Tier Detection ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_pipeline_detects_free_tier(client: AsyncClient, db: AsyncSession):
    """When no LLM config exists, pipeline run should have tier_at_run='free'."""
    resp = await client.post("/api/auth/register", json={
        "email": "free@test.com",
        "password": "testpass123",
        "full_name": "Free User",
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    with patch(_START):
        resp = await client.post("/api/pipeline/run", json={"skip_llm": True})
    assert resp.status_code == 202
    assert resp.json()["tier_at_run"] == "free"


@pytest.mark.asyncio
async def test_trigger_pipeline_detects_premium_tier(client: AsyncClient, db: AsyncSession):
    """When LLM config exists, pipeline run should have tier_at_run='premium'."""
    ws_id, token = await _setup_workspace_with_llm(db, client)

    with patch(_START) as mock_start:
        resp = await client.post("/api/pipeline/run", json={"skip_llm": True})
    assert resp.status_code == 202
    assert resp.json()["tier_at_run"] == "premium"
    call_kwargs = mock_start.call_args
    assert call_kwargs.kwargs["tier"] == "premium"


# ── Stage Reviews ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_reviews_empty(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)

    run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed, tier_at_run="premium")
    db.add(run)
    await db.commit()

    resp = await client.get(f"/api/pipeline/runs/{run.id}/reviews")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_reviews_with_pending(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)
    run_id, review_id = await _create_needs_review_run(db, ws_id)

    resp = await client.get(f"/api/pipeline/runs/{run_id}/reviews")
    assert resp.status_code == 200
    reviews = resp.json()
    assert len(reviews) == 1
    assert reviews[0]["id"] == review_id
    assert reviews[0]["status"] == "pending"
    assert reviews[0]["stage"] == "E1"


@pytest.mark.asyncio
async def test_approve_review(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)
    run_id, review_id = await _create_needs_review_run(db, ws_id)

    resp = await client.post(
        f"/api/pipeline/runs/{run_id}/reviews/{review_id}",
        json={"action": "approve", "reviewer_notes": "Looks good"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["reviewer_notes"] == "Looks good"
    assert data["reviewed_at"] is not None


@pytest.mark.asyncio
async def test_edit_review(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)
    run_id, review_id = await _create_needs_review_run(db, ws_id)

    edited = {"members": [{"key": "david", "full_name": "David FC"}]}
    resp = await client.post(
        f"/api/pipeline/runs/{run_id}/reviews/{review_id}",
        json={"action": "edit", "edited_output_json": edited, "reviewer_notes": "Fixed name"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "edited"
    assert data["edited_output_json"]["members"][0]["key"] == "david"


@pytest.mark.asyncio
async def test_edit_review_requires_output_json(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)
    run_id, review_id = await _create_needs_review_run(db, ws_id)

    resp = await client.post(
        f"/api/pipeline/runs/{run_id}/reviews/{review_id}",
        json={"action": "edit"},
    )
    assert resp.status_code == 400
    assert "edited_output_json" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_review_already_processed(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)
    run_id, review_id = await _create_needs_review_run(db, ws_id)

    await client.post(
        f"/api/pipeline/runs/{run_id}/reviews/{review_id}",
        json={"action": "approve"},
    )
    resp = await client.post(
        f"/api/pipeline/runs/{run_id}/reviews/{review_id}",
        json={"action": "approve"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_review_invalid_action(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)
    run_id, review_id = await _create_needs_review_run(db, ws_id)

    resp = await client.post(
        f"/api/pipeline/runs/{run_id}/reviews/{review_id}",
        json={"action": "reject"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_review_not_found(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)
    run_id, _ = await _create_needs_review_run(db, ws_id)

    resp = await client.post(
        f"/api/pipeline/runs/{run_id}/reviews/nonexistent-id",
        json={"action": "approve"},
    )
    assert resp.status_code == 404


# ── Resume ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resume_blocked_with_pending_reviews(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)
    run_id, review_id = await _create_needs_review_run(db, ws_id)

    resp = await client.post(f"/api/pipeline/runs/{run_id}/resume")
    assert resp.status_code == 409
    assert "reviews pendentes" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_resume_not_needs_review(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)

    run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed, tier_at_run="premium")
    db.add(run)
    await db.commit()

    resp = await client.post(f"/api/pipeline/runs/{run.id}/resume")
    assert resp.status_code == 409
    assert "não está pausada" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_resume_run_not_found(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)

    resp = await client.post("/api/pipeline/runs/nonexistent-id/resume")
    assert resp.status_code == 404


# ── Pipeline Response Schema ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pipeline_response_includes_tier_and_paused(client: AsyncClient, db: AsyncSession):
    ws_id, token = await _setup_workspace_with_llm(db, client)
    run_id, _ = await _create_needs_review_run(db, ws_id)

    resp = await client.get(f"/api/pipeline/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier_at_run"] == "premium"
    assert data["paused_at_stage"] == "E1"
    assert data["status"] == "needs_review"
