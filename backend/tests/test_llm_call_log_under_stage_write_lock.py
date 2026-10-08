"""Regressão — ``llm_call_log`` perdia toda call LLM feita após o 1º write do stage.

Medido no dogfood em 2026-10-08 (runs 3a5b9c7d, 7d860f0b, 40d1af2a): o E1.5a fez
10 calls LLM e gravou 1 row. A sessão de artefatos do stage segura o write-lock
do SQLite do 1º ``store.write`` até o commit no fim do stage ([[ADR-256]]); o
``record_call`` abria sessão própria, esperava o ``busy_timeout`` e estourava
``database is locked`` — engolido no choke-point do ``LLMService``.

SQLite em ARQUIVO, pool real e os pragmas de produção: o ``StaticPool`` dos
fixtures do backend entrega UMA conexão a todas as sessões, o que torna a
contenção impossível por construção — foi o que escondeu o defeito da suíte.
A testemunha é o que o stage recebeu do provedor, contado fora do ledger.
"""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

import backend.app.models  # noqa: F401 — registra todos os models no Base
from backend.app.core.database import Base, attach_sqlite_pragmas
from backend.app.core.security import hash_password
from backend.app.models.llm_call_log import LLMCallLog
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services import llm_budget_service as budget_mod
from backend.app.services.llm_budget_service import LLMBudgetService
from backend.app.services.pipeline.run_context_factory import HydratedContext
from backend.tests.fakes.fake_llm_client import FakeLLMClient
from pipeline.llm.call_hooks import LLMBudgetExceededError
from pipeline.llm.litellm_client import LLMCallResult, LLMConfig, LLMService
from pipeline.orchestrator import StageResult

# Produção espera 30s por chamada; o defeito é o mesmo com 200ms, o relógio não.
_TEST_BUSY_TIMEOUT_MS = 200
_CALLS_PER_STAGE = 4
_PROBE_ARTIFACT_STAGE = "llm_lock_probe"


class _ExtractedDoc(BaseModel):
    campo: str


def _short_busy_timeout(dbapi_conn, _record) -> None:
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute(f"PRAGMA busy_timeout={_TEST_BUSY_TIMEOUT_MS}")
    finally:
        cursor.close()


def _seed_run(factory, budget: Decimal = Decimal("50")) -> tuple[str, str]:
    with factory() as session:
        user = User(
            email=f"lock_{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=hash_password("p"),
            full_name="Lock",
        )
        session.add(user)
        session.flush()
        workspace = Workspace(name="WS", owner_id=user.id, monthly_llm_budget_usd=budget)
        session.add(workspace)
        session.flush()
        run = PipelineRun(workspace_id=workspace.id, status=PipelineRunStatus.running)
        session.add(run)
        session.commit()
        return workspace.id, run.id


@pytest.fixture()
def lock_prone_db(tmp_path, monkeypatch):
    """Engine em arquivo + QueuePool + WAL/FK de produção; ``SyncSessionLocal`` do loop apontado para ele."""
    import backend.app.tasks.pipeline_task as task_module

    engine = create_engine(
        f"sqlite:///{tmp_path / 'stage_lock.db'}", connect_args={"check_same_thread": False}
    )
    attach_sqlite_pragmas(engine)
    # Registrado depois do listener de produção: o PRAGMA dele (30s) é sobrescrito.
    event.listen(engine, "connect", _short_busy_timeout)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(task_module, "SyncSessionLocal", factory)
    monkeypatch.setattr(budget_mod, "_get_redis_safe", lambda: None)
    yield factory
    engine.dispose()


def _canned_response() -> _ExtractedDoc:
    output = _ExtractedDoc(campo="sintetico")
    usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=200)
    object.__setattr__(output, "_raw_response", SimpleNamespace(usage=usage))
    return output


@dataclass
class _ProviderBill:
    """O que o stage recebeu do provedor — contado fora do ledger, sob lock (há teste com threads)."""

    responses: int = 0
    paid: Decimal = Decimal("0")
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def call(self, hooks, stage: str) -> None:
        service = LLMService(
            LLMConfig(
                provider="anthropic",
                api_key="sk-test",
                model_name="claude-sonnet-4-6",
                call_hooks=hooks,
            )
        )
        service._ensure_client = lambda: None  # type: ignore[method-assign]
        service._client = FakeLLMClient(response=_canned_response())
        result = service.call(
            system_prompt="s", user_prompt="u", output_schema=_ExtractedDoc, stage=stage
        )
        with self._lock:
            self.responses += 1
            self.paid += Decimal(str(result.cost_estimate_usd))


def _sequential_stage(bill: _ProviderBill):
    """Espelha o loop do E1.5a: uma call LLM por documento e o write do artefato logo depois."""

    def _stage(ctx, stage: str) -> StageResult:
        for idx in range(_CALLS_PER_STAGE):
            bill.call(ctx.llm_call_hooks, stage)
            ctx.artifact_store.write(_PROBE_ARTIFACT_STAGE, f"doc-{idx}", {"idx": idx})
        return StageResult(stage=stage, success=True, duration_ms=1.0, detail={})

    return _stage


def _stage_failing_after_calls(bill: _ProviderBill):
    def _stage(ctx, stage: str) -> StageResult:
        _sequential_stage(bill)(ctx, stage)
        raise RuntimeError("fixture: falha deterministica depois das calls")

    return _stage


def _concurrent_stage(bill: _ProviderBill):
    """Espelha o extract_with_llm: calls em ThreadPoolExecutor com os hooks compartilhados."""

    def _stage(ctx, stage: str) -> StageResult:
        ctx.artifact_store.write(_PROBE_ARTIFACT_STAGE, "doc-0", {"idx": 0})
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(
                pool.map(
                    lambda _: bill.call(ctx.llm_call_hooks, stage), range(_CALLS_PER_STAGE * 2)
                )
            )
        return StageResult(stage=stage, success=True, duration_ms=1.0, detail={})

    return _stage


def _run_one_llm_stage(factory, ws_id: str, run_id: str, stage_fn) -> bool:
    from backend.app.tasks.pipeline_task import _execute_stages_loop

    hooks = LLMBudgetService.for_pipeline_run(ws_id, run_id, session_factory=factory)
    ctx = SimpleNamespace(artifact_store=None, llm_call_hooks=hooks, config_overrides=None)
    has_failure, _paused = _execute_stages_loop(
        ctx,
        stages=["extract_baseline"],
        run_id=run_id,
        ws_id=ws_id,
        skip_llm=False,
        stop_on_error=True,
        tier="premium",
        llm_stages={"extract_baseline"},
        run_stage_fn=stage_fn,
    )
    return has_failure


def _artifact_count(factory, run_id: str) -> int:
    with factory() as session:
        return session.execute(
            select(func.count())
            .select_from(PipelineArtifact)
            .where(PipelineArtifact.pipeline_run_id == run_id)
        ).scalar_one()


def _ledger(factory, run_id: str) -> tuple[int, Decimal]:
    """(rows, soma de cost_usd) do run em ``llm_call_log``."""
    with factory() as session:
        rows, total = session.execute(
            select(func.count(), func.coalesce(func.sum(LLMCallLog.cost_usd), 0)).where(
                LLMCallLog.pipeline_run_id == run_id
            )
        ).one()
    return rows, Decimal(total)


def test_every_call_of_a_multi_call_stage_lands_in_llm_call_log(lock_prone_db) -> None:
    ws_id, run_id = _seed_run(lock_prone_db)
    bill = _ProviderBill()

    has_failure = _run_one_llm_stage(lock_prone_db, ws_id, run_id, _sequential_stage(bill))

    assert not has_failure
    assert _artifact_count(lock_prone_db, run_id) == _CALLS_PER_STAGE
    assert bill.responses == _CALLS_PER_STAGE
    assert _ledger(lock_prone_db, run_id) == (bill.responses, bill.paid)


def test_rolled_back_stage_still_records_the_calls_it_paid(lock_prone_db) -> None:
    ws_id, run_id = _seed_run(lock_prone_db)
    bill = _ProviderBill()

    has_failure = _run_one_llm_stage(lock_prone_db, ws_id, run_id, _stage_failing_after_calls(bill))

    assert has_failure
    assert _artifact_count(lock_prone_db, run_id) == 0
    assert _ledger(lock_prone_db, run_id) == (bill.responses, bill.paid)


def test_concurrent_calls_in_one_stage_are_all_recorded(lock_prone_db) -> None:
    ws_id, run_id = _seed_run(lock_prone_db)
    bill = _ProviderBill()

    has_failure = _run_one_llm_stage(lock_prone_db, ws_id, run_id, _concurrent_stage(bill))

    assert not has_failure
    assert bill.responses == _CALLS_PER_STAGE * 2
    assert _ledger(lock_prone_db, run_id) == (bill.responses, bill.paid)


# --- o buffer em si: falha contável, hard-stop, idempotência, dialect ---------


def _result(cost_usd: Decimal = Decimal("0.0123")) -> LLMCallResult:
    return LLMCallResult(
        output=None,
        provider="anthropic",
        model="claude-test",
        tokens_in=100,
        tokens_out=50,
        total_tokens=150,
        # O campo é float por contrato (telemetria); o ledger guarda Numeric.
        cost_estimate_usd=float(cost_usd),
        duration_ms=1200,
    )


class _RecordingLogger:
    """Captura o ERROR do flush — imune a propagate=False do namespace mathoms.*."""

    def __init__(self) -> None:
        self.errors: list[dict] = []

    def error(self, msg: str, *args, extra: dict | None = None, **kwargs) -> None:
        self.errors.append({"msg": msg, **(extra or {})})


@contextmanager
def _write_lock_held_elsewhere(factory):
    """Outra conexão segura o writer único do SQLite — a falha de flush é real, não mock."""
    session = factory()
    try:
        session.execute(text("UPDATE workspaces SET name = name"))
        yield
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def flush_blocked_once(lock_prone_db, monkeypatch):
    """2 calls adiadas cujo 1º flush esbarra no writer único preso por outra conexão."""
    ws_id, run_id = _seed_run(lock_prone_db)
    failures = _RecordingLogger()
    monkeypatch.setattr(budget_mod, "_call_log_failures", failures)
    hooks = LLMBudgetService.for_pipeline_run(ws_id, run_id, session_factory=lock_prone_db)
    for stage in ("extract_informe_aluguel:doc_sintetico.pdf", "extract_baseline"):
        hooks.record_call(_result(), stage=stage, prompt_version=None)
    with _write_lock_held_elsewhere(lock_prone_db):
        hooks.flush_call_log()
    return SimpleNamespace(hooks=hooks, failures=failures, run_id=run_id, db=lock_prone_db)


def test_failed_flush_is_a_countable_error_with_a_pii_free_dead_letter(flush_blocked_once) -> None:
    [failure] = flush_blocked_once.failures.errors

    assert _ledger(flush_blocked_once.db, flush_blocked_once.run_id) == (0, Decimal("0"))
    assert (failure["rows"], failure["cost_usd"], failure["error_class"]) == (
        2,
        "0.0246",
        "OperationalError",
    )
    assert [row["stage"] for row in failure["dead_letter"]] == [
        "extract_informe_aluguel",
        "extract_baseline",
    ]


def test_failed_flush_keeps_the_calls_pending_until_the_next_flush(flush_blocked_once) -> None:
    flush_blocked_once.hooks.flush_call_log()

    assert _ledger(flush_blocked_once.db, flush_blocked_once.run_id) == (2, Decimal("0.0246"))
    assert len(flush_blocked_once.failures.errors) == 1


def test_pending_spend_alone_trips_the_hard_stop(lock_prone_db) -> None:
    ws_id, run_id = _seed_run(lock_prone_db, budget=Decimal("0.01"))
    hooks = LLMBudgetService.for_pipeline_run(ws_id, run_id, session_factory=lock_prone_db)
    hooks.check_budget()

    hooks.record_call(
        _result(cost_usd=Decimal("0.02")), stage="extract_baseline", prompt_version=None
    )

    assert _ledger(lock_prone_db, run_id) == (0, Decimal("0"))
    with pytest.raises(LLMBudgetExceededError):
        hooks.check_budget()


def test_reflush_with_an_already_committed_row_still_lands_the_new_ones(lock_prone_db) -> None:
    """Ack perdido: a row volta ao pendente com o commit já aterrissado, ao lado de uma nova.

    Sem ``ON CONFLICT`` o lote inteiro aborta na PK — a nova nunca grava e a
    velha fica contada duas vezes no hard-stop (DB + pendente).
    """
    ws_id, run_id = _seed_run(lock_prone_db)
    hooks = LLMBudgetService.for_pipeline_run(ws_id, run_id, session_factory=lock_prone_db)
    hooks.record_call(_result(), stage="extract_baseline", prompt_version=None)
    lost_ack = list(hooks._pending)
    hooks.flush_call_log()

    hooks._pending.extend(lost_ack)
    hooks.record_call(
        _result(cost_usd=Decimal("0.02")), stage="extract_baseline", prompt_version=None
    )
    hooks.flush_call_log()

    assert _ledger(lock_prone_db, run_id) == (2, Decimal("0.0323"))


def test_hydrated_context_close_flushes_the_per_stage_instance(lock_prone_db) -> None:
    """Executor HTTP/CLI cria os hooks por stage: o close do contexto é o último flush."""
    ws_id, run_id = _seed_run(lock_prone_db)
    hooks = LLMBudgetService.for_pipeline_run(ws_id, run_id, session_factory=lock_prone_db)
    hooks.record_call(_result(), stage="extract_baseline", prompt_version=None)

    HydratedContext(
        ctx=SimpleNamespace(llm_call_hooks=hooks), config_store_session=lock_prone_db()
    ).close()

    assert _ledger(lock_prone_db, run_id) == (1, Decimal("0.0123"))


def test_postgres_run_hooks_still_write_at_call_time() -> None:
    """Sem writer único não há o que adiar: a call tenta gravar na hora (aqui, sem servidor)."""
    engine = create_engine("postgresql+psycopg://u:p@127.0.0.1:1/never")
    hooks = LLMBudgetService.for_pipeline_run(
        "ws", "run", session_factory=sessionmaker(bind=engine)
    )

    with pytest.raises(OperationalError):
        hooks.record_call(_result(), stage="extract_baseline", prompt_version=None)
    engine.dispose()
