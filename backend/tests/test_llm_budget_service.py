"""``LLMBudgetService`` — thresholds 80%/110% + persistência ``LLMCallLog`` (ADR-173)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models import User, Workspace
from backend.app.models.llm_call_log import LLMCallLog
from backend.app.services import llm_budget_service as budget_mod
from backend.app.services.llm_budget_service import LLMBudgetService
from pipeline.llm.call_hooks import LLMBudgetExceededError
from pipeline.llm.litellm_client import LLMCallResult


@pytest.fixture()
def session_factory(monkeypatch):
    """Engine sqlite in-memory compartilhado (DB nunca é mocado) + Redis off."""
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(budget_mod, "_get_redis_safe", lambda: None)
    yield factory
    engine.dispose()


def _seed_workspace(factory, budget: Decimal | None) -> str:
    session = factory()
    try:
        user = User(email="fin@test.com", hashed_password=hash_password("p"), full_name="U")
        session.add(user)
        session.flush()
        ws = Workspace(name="WS", owner_id=user.id, monthly_llm_budget_usd=budget)
        session.add(ws)
        session.flush()
        if budget is None:
            # default=5.00 dispara no INSERT quando o valor é None — NULL
            # (sem cap) só existe via UPDATE, mesmo caminho do admin real.
            ws.monthly_llm_budget_usd = None
        session.commit()
        return ws.id
    finally:
        session.close()


def _spend(factory, ws_id: str, amount: str) -> None:
    session = factory()
    try:
        session.add(
            LLMCallLog(
                workspace_id=ws_id,
                stage="E1",
                model_name="claude-test",
                tokens_in=100,
                tokens_out=50,
                cost_usd=Decimal(amount),
            )
        )
        session.commit()
    finally:
        session.close()


def _result(cost: float = 0.01) -> LLMCallResult:
    return LLMCallResult(
        output=None,
        provider="anthropic",
        model="claude-test",
        tokens_in=100,
        tokens_out=50,
        total_tokens=150,
        cost_estimate_usd=cost,
        duration_ms=1200,
    )


def test_null_budget_is_unlimited(session_factory) -> None:
    ws_id = _seed_workspace(session_factory, budget=None)
    _spend(session_factory, ws_id, "999.00")
    LLMBudgetService(ws_id, session_factory=session_factory).check_budget()


class _RecordingBudgetLogger:
    """Captura eventos do logger de métrica — imune a propagate=False do namespace
    mathoms.* (setup de logging de outro teste da suíte deixa caplog vazio)."""

    def __init__(self) -> None:
        self.events: list[str] = []

    def warning(self, msg: str, *args, **kwargs) -> None:
        self.events.append(msg)


def test_under_warn_threshold_passes_silently(session_factory, monkeypatch) -> None:
    recorder = _RecordingBudgetLogger()
    monkeypatch.setattr(budget_mod, "_budget_metrics", recorder)
    ws_id = _seed_workspace(session_factory, budget=Decimal("10.00"))
    _spend(session_factory, ws_id, "7.00")
    LLMBudgetService(ws_id, session_factory=session_factory).check_budget()
    assert recorder.events == []


def test_warn_at_80_percent_does_not_block(session_factory, monkeypatch) -> None:
    recorder = _RecordingBudgetLogger()
    monkeypatch.setattr(budget_mod, "_budget_metrics", recorder)
    ws_id = _seed_workspace(session_factory, budget=Decimal("10.00"))
    _spend(session_factory, ws_id, "8.50")
    LLMBudgetService(ws_id, session_factory=session_factory).check_budget()
    assert recorder.events == ["llm budget warn"]


def test_hard_stop_at_110_percent(session_factory) -> None:
    ws_id = _seed_workspace(session_factory, budget=Decimal("10.00"))
    _spend(session_factory, ws_id, "11.00")
    with pytest.raises(LLMBudgetExceededError) as exc_info:
        LLMBudgetService(ws_id, session_factory=session_factory).check_budget()
    assert exc_info.value.workspace_id == ws_id


def test_record_call_persists_row(session_factory) -> None:
    ws_id = _seed_workspace(session_factory, budget=Decimal("10.00"))
    svc = LLMBudgetService(ws_id, pipeline_run_id="run-42", session_factory=session_factory)

    svc.record_call(_result(cost=0.0123), stage="E1.5", prompt_version="e15:v2")

    session = session_factory()
    try:
        row = session.execute(select(LLMCallLog)).scalar_one()
    finally:
        session.close()
    assert row.workspace_id == ws_id
    assert row.stage == "E1.5"
    assert row.prompt_version == "e15:v2"
    assert row.pipeline_run_id == "run-42"
    assert row.cost_usd == Decimal("0.0123")
    assert row.tokens_in == 100 and row.tokens_out == 50


def test_recorded_spend_feeds_next_check(session_factory) -> None:
    ws_id = _seed_workspace(session_factory, budget=Decimal("0.01"))
    svc = LLMBudgetService(ws_id, session_factory=session_factory)

    svc.check_budget()
    svc.record_call(_result(cost=0.02), stage="E1", prompt_version=None)

    with pytest.raises(LLMBudgetExceededError):
        svc.check_budget()


class _SpyRedis:
    """Gasto stale fixo — o cap novo (lido fresh do DB) decide mesmo assim."""

    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def get(self, key):
        self._calls.append(f"get:{key}")
        return b"5.57"

    def set(self, *args, **kwargs):
        self._calls.append("set")


def _set_cap(factory, ws_id: str, value: Decimal) -> None:
    session = factory()
    try:
        session.get(Workspace, ws_id).monthly_llm_budget_usd = value
        session.commit()
    finally:
        session.close()


def test_cap_update_effective_without_cache_invalidation(session_factory, monkeypatch) -> None:
    """A30.l1: editar o cap (mesmo UPDATE do editor admin) vale no próximo
    check_budget SEM invalidar o cache Redis de gasto."""
    ws_id = _seed_workspace(session_factory, budget=Decimal("5.00"))
    _spend(session_factory, ws_id, "5.57")
    service = LLMBudgetService(ws_id, session_factory=session_factory)
    with pytest.raises(LLMBudgetExceededError):
        service.check_budget()
    redis_calls: list[str] = []
    monkeypatch.setattr(budget_mod, "_get_redis_safe", lambda: _SpyRedis(redis_calls))
    _set_cap(session_factory, ws_id, Decimal("20.00"))
    service.check_budget()
    assert "set" not in redis_calls
