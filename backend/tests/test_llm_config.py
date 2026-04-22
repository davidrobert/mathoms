"""Tests for Phase 4A: LLMConfig model, API endpoints, schemas, tier detection."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.llm_config import LLMConfig
from backend.app.models.workspace import Workspace
from backend.app.services.vault import VaultService

_vault = VaultService()


# =============================================================================
# Model tests
# =============================================================================


@pytest.mark.asyncio
async def test_llm_config_model_creation(db: AsyncSession):
    """LLMConfig can be created with encrypted API key."""
    from backend.app.models.user import User

    user = User(email="llm@test.com", hashed_password="hash", full_name="LLM User")
    db.add(user)
    await db.flush()

    ws = Workspace(name="Test WS", owner_id=user.id)
    db.add(ws)
    await db.flush()

    cfg = LLMConfig(
        workspace_id=ws.id,
        provider="anthropic",
        api_key_encrypted=_vault.encrypt("sk-ant-test-key-12345"),
        model_name="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.1,
    )
    db.add(cfg)
    await db.commit()

    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == ws.id))
    saved = result.scalar_one()
    assert saved.provider == "anthropic"
    assert saved.model_name == "claude-sonnet-4-20250514"
    assert saved.max_tokens == 4096
    assert saved.temperature == 0.1

    decrypted = _vault.decrypt(saved.api_key_encrypted)
    assert decrypted == "sk-ant-test-key-12345"


@pytest.mark.asyncio
async def test_llm_config_workspace_unique(db: AsyncSession):
    """Only one LLMConfig per workspace."""
    from sqlalchemy.exc import IntegrityError

    from backend.app.models.user import User

    user = User(email="llm2@test.com", hashed_password="hash", full_name="LLM User 2")
    db.add(user)
    await db.flush()

    ws = Workspace(name="Test WS2", owner_id=user.id)
    db.add(ws)
    await db.flush()

    cfg1 = LLMConfig(
        workspace_id=ws.id, provider="anthropic", api_key_encrypted="enc1", model_name="m1"
    )
    db.add(cfg1)
    await db.commit()

    cfg2 = LLMConfig(
        workspace_id=ws.id, provider="openai", api_key_encrypted="enc2", model_name="m2"
    )
    db.add(cfg2)
    with pytest.raises(IntegrityError):
        await db.commit()


# =============================================================================
# StageReview model tests
# =============================================================================


@pytest.mark.asyncio
async def test_stage_review_model_creation(db: AsyncSession):
    """StageReview can be created linked to a PipelineRun."""
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
    from backend.app.models.stage_review import StageReview, StageReviewStatus
    from backend.app.models.user import User

    user = User(email="sr@test.com", hashed_password="hash", full_name="SR User")
    db.add(user)
    await db.flush()

    ws = Workspace(name="Test SR WS", owner_id=user.id)
    db.add(ws)
    await db.flush()

    run = PipelineRun(
        workspace_id=ws.id, status=PipelineRunStatus.needs_review, tier_at_run="premium"
    )
    db.add(run)
    await db.flush()

    review = StageReview(
        pipeline_run_id=run.id,
        stage="E2-llm",
        status=StageReviewStatus.pending,
        original_output_json={"transactions": []},
        validation_errors="confidence < 0.7",
    )
    db.add(review)
    await db.commit()

    result = await db.execute(select(StageReview).where(StageReview.pipeline_run_id == run.id))
    saved = result.scalar_one()
    assert saved.stage == "E2-llm"
    assert saved.status == StageReviewStatus.pending
    assert saved.original_output_json == {"transactions": []}


# =============================================================================
# Pipeline run status expansion tests
# =============================================================================


@pytest.mark.asyncio
async def test_pipeline_run_new_statuses(db: AsyncSession):
    """PipelineRun supports needs_review, resuming statuses and tier_at_run."""
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
    from backend.app.models.user import User

    user = User(email="status@test.com", hashed_password="hash", full_name="Status User")
    db.add(user)
    await db.flush()

    ws = Workspace(name="Status WS", owner_id=user.id)
    db.add(ws)
    await db.flush()

    run = PipelineRun(
        workspace_id=ws.id,
        status=PipelineRunStatus.needs_review,
        tier_at_run="premium",
        paused_at_stage="E2-llm",
    )
    db.add(run)
    await db.commit()

    result = await db.execute(select(PipelineRun).where(PipelineRun.id == run.id))
    saved = result.scalar_one()
    assert saved.status == PipelineRunStatus.needs_review
    assert saved.tier_at_run == "premium"
    assert saved.paused_at_stage == "E2-llm"

    saved.status = PipelineRunStatus.resuming
    await db.commit()

    result = await db.execute(select(PipelineRun).where(PipelineRun.id == run.id))
    assert result.scalar_one().status == PipelineRunStatus.resuming


@pytest.mark.asyncio
async def test_pipeline_stage_skipped_free_tier(db: AsyncSession):
    """PipelineStageLog supports skipped_free_tier status."""
    from backend.app.models.pipeline_run import PipelineRun, PipelineStageLog, PipelineStageStatus
    from backend.app.models.user import User

    user = User(email="skip@test.com", hashed_password="hash", full_name="Skip User")
    db.add(user)
    await db.flush()

    ws = Workspace(name="Skip WS", owner_id=user.id)
    db.add(ws)
    await db.flush()

    run = PipelineRun(workspace_id=ws.id, tier_at_run="free")
    db.add(run)
    await db.flush()

    log = PipelineStageLog(
        pipeline_run_id=run.id,
        stage="E1",
        status=PipelineStageStatus.skipped_free_tier,
    )
    db.add(log)
    await db.commit()

    result = await db.execute(
        select(PipelineStageLog).where(PipelineStageLog.pipeline_run_id == run.id)
    )
    saved = result.scalar_one()
    assert saved.status == PipelineStageStatus.skipped_free_tier


# =============================================================================
# API tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_llm_config_empty(auth_client: AsyncClient):
    """GET /api/config/llm returns null when no config exists."""
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/llm")
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_save_and_get_llm_config(auth_client: AsyncClient):
    """PUT /api/config/llm saves config with encrypted key, GET returns masked key."""
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "anthropic",
            "api_key": "sk-ant-api03-REAL-KEY-HERE-1234567890",
            "model_name": "claude-sonnet-4-20250514",
            "max_tokens": 8192,
            "temperature": 0.2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "anthropic"
    assert data["model_name"] == "claude-sonnet-4-20250514"
    assert data["max_tokens"] == 8192
    assert data["temperature"] == 0.2
    assert "sk-a" in data["api_key_masked"]
    assert "7890" in data["api_key_masked"]
    assert "REAL-KEY-HERE" not in data["api_key_masked"]

    get_resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/llm")
    assert get_resp.status_code == 200
    assert get_resp.json()["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_update_llm_config(auth_client: AsyncClient):
    """PUT /api/config/llm updates existing config."""
    await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "anthropic",
            "api_key": "sk-ant-first-key",
            "model_name": "claude-sonnet-4-20250514",
        },
    )

    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "openai",
            "api_key": "sk-openai-new-key",
            "model_name": "gpt-4o",
            "max_tokens": 16384,
            "temperature": 0.5,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "openai"
    assert data["model_name"] == "gpt-4o"
    assert data["max_tokens"] == 16384


@pytest.mark.asyncio
async def test_delete_llm_config(auth_client: AsyncClient):
    """DELETE /api/config/llm removes config."""
    await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "anthropic",
            "api_key": "sk-ant-delete-test",
        },
    )

    resp = await auth_client.delete(f"/api/workspaces/{auth_client.ws_id}/config/llm")
    assert resp.status_code == 204

    get_resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/llm")
    assert get_resp.json() is None


@pytest.mark.asyncio
async def test_delete_llm_config_not_found(auth_client: AsyncClient):
    """DELETE /api/config/llm returns 404 when no config."""
    resp = await auth_client.delete(f"/api/workspaces/{auth_client.ws_id}/config/llm")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_provider_rejected(auth_client: AsyncClient):
    """PUT /api/config/llm rejects invalid provider."""
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "invalid_provider",
            "api_key": "some-key",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_empty_api_key_rejected(auth_client: AsyncClient):
    """PUT /api/config/llm rejects empty API key."""
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "anthropic",
            "api_key": "",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_tier_free_by_default(auth_client: AsyncClient):
    """GET /api/config/llm/tier returns 'free' when no LLM config."""
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/llm/tier")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "free"
    assert data["has_llm_config"] is False


@pytest.mark.asyncio
async def test_tier_premium_with_config(auth_client: AsyncClient):
    """GET /api/config/llm/tier returns 'premium' when LLM config exists."""
    await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "anthropic",
            "api_key": "sk-ant-test-key",
        },
    )

    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/llm/tier")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "premium"
    assert data["has_llm_config"] is True
    assert data["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_test_connection_no_config(auth_client: AsyncClient):
    """POST /api/config/llm/test returns 404 when no config and no api_key override."""
    resp = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/config/llm/test", json={})
    assert resp.status_code == 404


# =============================================================================
# Schema validation tests
# =============================================================================


@pytest.mark.asyncio
async def test_max_tokens_bounds(auth_client: AsyncClient):
    """max_tokens must be between 1 and 200000."""
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "anthropic",
            "api_key": "sk-test",
            "max_tokens": 0,
        },
    )
    assert resp.status_code == 422

    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "anthropic",
            "api_key": "sk-test",
            "max_tokens": 200001,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_temperature_bounds(auth_client: AsyncClient):
    """temperature must be between 0.0 and 2.0."""
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "anthropic",
            "api_key": "sk-test",
            "temperature": -0.1,
        },
    )
    assert resp.status_code == 422

    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "anthropic",
            "api_key": "sk-test",
            "temperature": 2.1,
        },
    )
    assert resp.status_code == 422
