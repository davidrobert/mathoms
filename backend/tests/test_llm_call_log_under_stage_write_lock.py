"""Regressão — ``llm_call_log`` perdia toda call LLM feita após o 1º write do stage.

Medido no dogfood em 2026-10-08 (runs 3a5b9c7d, 7d860f0b, 40d1af2a): o E1.5a fez
10 calls LLM e gravou 1 row. A sessão de artefatos do stage segura o write-lock
do SQLite do 1º ``store.write`` até o commit no fim do stage ([[ADR-256]]); o
``record_call`` abria sessão própria, esperava o ``busy_timeout`` e estourava
``database is locked`` — engolido no choke-point do ``LLMService``.

SQLite em ARQUIVO, pool real e os pragmas de produção: o ``StaticPool`` dos
fixtures do backend entrega UMA conexão a todas as sessões, o que torna a
contenção impossível por construção — foi o que escondeu o defeito da suíte.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine, event, func, select
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
from backend.tests.fakes.fake_llm_client import FakeLLMClient
from pipeline.llm.litellm_client import LLMConfig, LLMService
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


def _seed_run(factory) -> tuple[str, str]:
    with factory() as session:
        user = User(
            email=f"lock_{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=hash_password("p"),
            full_name="Lock",
        )
        session.add(user)
        session.flush()
        workspace = Workspace(name="WS", owner_id=user.id, monthly_llm_budget_usd=Decimal("50"))
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


def _multi_call_stage(ctx, stage: str) -> StageResult:
    """Espelha o loop do E1.5a: uma call LLM por documento e o write do artefato logo depois."""
    service = LLMService(
        LLMConfig(
            provider="anthropic",
            api_key="sk-test",
            model_name="claude-sonnet-4-6",
            call_hooks=ctx.llm_call_hooks,
        )
    )
    service._ensure_client = lambda: None  # type: ignore[method-assign]
    service._client = FakeLLMClient(response=_canned_response())
    for idx in range(_CALLS_PER_STAGE):
        service.call(system_prompt="s", user_prompt="u", output_schema=_ExtractedDoc, stage=stage)
        ctx.artifact_store.write(_PROBE_ARTIFACT_STAGE, f"doc-{idx}", {"idx": idx})
    return StageResult(stage=stage, success=True, duration_ms=1.0, detail={})


def _run_one_llm_stage(factory, ws_id: str, run_id: str, stage_fn) -> bool:
    from backend.app.tasks.pipeline_task import _execute_stages_loop

    hooks = LLMBudgetService(ws_id, pipeline_run_id=run_id, session_factory=factory)
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


def _count(factory, model, run_id: str) -> int:
    with factory() as session:
        return session.execute(
            select(func.count()).select_from(model).where(model.pipeline_run_id == run_id)
        ).scalar_one()


def test_every_llm_call_of_a_multi_call_stage_lands_in_llm_call_log(lock_prone_db) -> None:
    ws_id, run_id = _seed_run(lock_prone_db)

    has_failure = _run_one_llm_stage(lock_prone_db, ws_id, run_id, _multi_call_stage)

    assert not has_failure
    assert _count(lock_prone_db, PipelineArtifact, run_id) == _CALLS_PER_STAGE
    assert _count(lock_prone_db, LLMCallLog, run_id) == _CALLS_PER_STAGE
