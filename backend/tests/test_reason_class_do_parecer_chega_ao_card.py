"""ADR-447 — a falha de LLM do parecer chega ao card de `/admin/metrics` com a classe certa."""

# Gate de não-inércia. Os stages que deixam a exceção tipada chegar ao `_run_stage`
# são `required` e terminam `failed`, fora do card; o único degradável com falha de
# LLM é o parecer, e ele a captura em `_call_llm_safe`. Consertar só o `except` do
# `_run_stage` virava o xfail da ADR-443 em verde sem mover o card. Aqui tudo é de
# produção — runner do parecer, `generate_parecer`, `LLMService` com o próprio retry,
# client in-process, loop e a query do card —; só o hook de budget e o client do
# provider são falsos.

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from backend.app.models.pipeline_run import PipelineStageLog
from backend.app.services.internal_ops.degradation_metrics import cutoff_for, degraded_stages
from backend.app.services.pipeline import pipeline_client as pc
from backend.app.services.storage.llm_cache import InMemoryLLMCache
from backend.tests.test_stage_degradation import (  # noqa: F401 — `seeded` é fixture
    _E5_KEY,
    _E5_PAYLOAD,
    _E5_STAGE,
    _PARECER,
    seeded,
)
from pipeline.llm.call_hooks import LLMBudgetExceededError


class _BudgetHardStop:
    """`LLMCallHooks` cujo pré-call estoura — o real (`LLMBudgetService`) lê o gasto do DB."""

    def check_budget(self) -> None:
        raise LLMBudgetExceededError("ws-sintetico", Decimal("11.00"), Decimal("10.00"))

    def record_call(self, result, *, stage, prompt_version) -> None:
        pytest.fail("budget estourado não pode chegar ao provider")


def _provider_timing_out(monkeypatch) -> None:
    """Client do provider que estoura o cap em toda tentativa; o retry é o do `LLMService`."""
    import backend.app.services.parecer_orchestrator as orchestrator_module

    real_build = orchestrator_module._build_llm_service
    monkeypatch.setattr("pipeline.llm.litellm_client.time.sleep", lambda _s: None)

    def _build(config):
        service = real_build(config)
        service._ensure_client = lambda: None
        service._client = MagicMock()
        timeout = TimeoutError("litellm.Timeout: Request timed out")
        service._client.chat.completions.create.side_effect = timeout
        return service

    monkeypatch.setattr(orchestrator_module, "_build_llm_service", _build)


def _production_ctx(seed: dict, hooks) -> SimpleNamespace:
    """O que o runner do parecer lê do `WorkspaceContext` — store, config e hooks."""
    configs = {"llm_config.json": {"api_key": "sk-sintetica"}}
    ctx = SimpleNamespace(
        artifact_store=None,
        root=seed["tmp_path"],
        pipeline_run_id=seed["run_id"],
        workspace_id=seed["ws_id"],
        llm_call_hooks=hooks,
        load_config=configs.get,
    )
    ctx.get_artifact_store = lambda: ctx.artifact_store
    return ctx


def _run_e5_then_real_parecer(seed: dict, ctx, monkeypatch) -> None:
    import backend.app.services.parecer_orchestrator as orchestrator_module
    import pipeline.orchestrator as orchestrator
    from backend.app.tasks.pipeline_task import _execute_stages_loop

    real_runner = orchestrator._get_stage_runner

    def _e5_writer(stage_ctx):
        stage_ctx.artifact_store.write(_E5_STAGE, _E5_KEY, dict(_E5_PAYLOAD))
        return {"ok": True}

    monkeypatch.setattr(
        orchestrator,
        "_get_stage_runner",
        lambda s: _e5_writer if s == _E5_STAGE else real_runner(s),
    )
    monkeypatch.setattr(orchestrator_module, "_build_cache", InMemoryLLMCache)
    monkeypatch.delenv("MATHOMS_PIPELINE_SERVICE_URL", raising=False)
    pc.reset_pipeline_client()
    client = pc.get_pipeline_client()
    assert isinstance(client, pc.InProcessPipelineClient)
    _execute_stages_loop(
        ctx,
        stages=[_E5_STAGE, _PARECER],
        run_id=seed["run_id"],
        ws_id=seed["ws_id"],
        skip_llm=False,
        stop_on_error=True,
        tier="premium",
        llm_stages={_PARECER},
        run_stage_fn=lambda c, s: client.execute_stage(c, s, workspace_id=seed["ws_id"]),
    )
    pc.reset_pipeline_client()


async def _parecer_log(seed: dict) -> PipelineStageLog:
    async with seed["async_session"]() as db:
        query = select(PipelineStageLog).where(
            PipelineStageLog.pipeline_run_id == seed["run_id"], PipelineStageLog.stage == _PARECER
        )
        return (await db.execute(query)).scalar_one()


@pytest.mark.parametrize(
    ("hooks", "provider_down", "expected"),
    [
        pytest.param(_BudgetHardStop(), False, "budget_exhausted", id="budget"),
        pytest.param(None, True, "timeout", id="llm-timeout"),
    ],
)
@pytest.mark.asyncio
async def test_falha_de_llm_do_parecer_chega_ao_card(
    hooks, provider_down, expected, seeded, monkeypatch
):
    if provider_down:
        _provider_timing_out(monkeypatch)

    _run_e5_then_real_parecer(seeded, _production_ctx(seeded, hooks), monkeypatch)

    log = await _parecer_log(seeded)
    assert log.status.value == "degraded"
    assert log.output_summary["failure_class"] == expected
    assert log.output_summary["reason_class"] == expected
    async with seeded["async_session"]() as db:
        by_reason, by_stage = await degraded_stages(db, cutoff=cutoff_for(30))
    assert by_stage == {_PARECER: 1}
    assert {r: n for r, n in by_reason.items() if n} == {expected: 1}
