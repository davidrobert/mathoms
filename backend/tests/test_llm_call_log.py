"""Tests para LLMCallLog model + LLMCallLogRepository (post-review fix 0.3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models import User, Workspace
from backend.app.repositories.llm_call_log_repository import LLMCallLogRepository


async def _seed_ws(db: AsyncSession, *, email: str = "fin@test.com") -> str:
    user = User(email=email, hashed_password=hash_password("p"), full_name="U")
    db.add(user)
    await db.flush()
    ws = Workspace(name="WS", owner_id=user.id, monthly_llm_budget_usd=Decimal("10.00"))
    db.add(ws)
    await db.flush()
    return ws.id


async def _record(repo, ws_id, **overrides):
    """Helper de teste — defaults sensatos para não poluir cada caso."""
    defaults = dict(
        workspace_id=ws_id,
        stage="extract_irpf_full",
        model_name="claude-sonnet-4-5",
        tokens_in=1000,
        tokens_out=500,
        cost_usd=Decimal("0.012"),
        cost_known=True,
        duration_ms=2000,
    )
    defaults.update(overrides)
    return await repo.record(**defaults)


@pytest.mark.asyncio
async def test_record_persists_call(db: AsyncSession) -> None:
    ws_id = await _seed_ws(db)
    row = await _record(LLMCallLogRepository(db), ws_id, prompt_version="e16:v3")
    await db.commit()
    assert row.id and row.workspace_id == ws_id


_UNKNOWN_MODEL_KW = dict(
    stage="generate_narratives",
    model_name="custom-modelo-novo-9000",
    tokens_in=2000,
    tokens_out=1000,
    cost_usd=Decimal("0"),
    cost_known=False,
)


@pytest.mark.asyncio
async def test_spend_in_period_aggregates(db: AsyncSession) -> None:
    ws_id = await _seed_ws(db, email="fin-spend@test.com")
    repo = LLMCallLogRepository(db)
    await _record(repo, ws_id, stage="extract_members", cost_usd=Decimal("0.012"))
    await _record(repo, ws_id, tokens_in=15000, tokens_out=8000, cost_usd=Decimal("0.165"))
    await _record(repo, ws_id, **_UNKNOWN_MODEL_KW)
    await db.commit()

    since = datetime.now(timezone.utc) - timedelta(days=30)
    summary = await repo.spend_in_period(workspace_id=ws_id, since=since)
    assert summary.call_count == 3
    assert summary.total_cost_usd == Decimal("0.177000")
    assert summary.unknown_cost_calls == 1


@pytest.mark.asyncio
async def test_spend_filtered_by_window(db: AsyncSession) -> None:
    ws_id = await _seed_ws(db, email="fin-window@test.com")
    repo = LLMCallLogRepository(db)
    await _record(repo, ws_id, cost_usd=Decimal("0.50"))
    await db.commit()

    future = datetime.now(timezone.utc) + timedelta(days=1)
    summary = await repo.spend_in_period(
        workspace_id=ws_id, since=future, until=future + timedelta(days=1)
    )
    assert summary.call_count == 0
    assert summary.total_cost_usd == Decimal("0")


@pytest.mark.asyncio
async def test_by_workspace_summary_orders_by_spend_desc(db: AsyncSession) -> None:
    ws_a = await _seed_ws(db, email="ws-a@test.com")
    ws_b = await _seed_ws(db, email="ws-b@test.com")
    repo = LLMCallLogRepository(db)
    await _record(repo, ws_a, cost_usd=Decimal("0.10"))
    await _record(repo, ws_b, model_name="claude-opus-4", cost_usd=Decimal("5.00"))
    await db.commit()

    since = datetime.now(timezone.utc) - timedelta(days=1)
    summaries = await repo.by_workspace_summary(since=since)
    assert [s.workspace_id for s in summaries] == [ws_b, ws_a]
    assert summaries[0].total_cost_usd == Decimal("5.000000")
