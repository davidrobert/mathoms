"""O soft time limit encerra o run: nenhum stage começa depois dele e o desfecho tem motivo."""

# `SoftTimeLimitExceeded` é `Exception` pura (billiard). O `except Exception` de
# `orchestrator._run_stage` o achatava em `StageResult(success=False)` e o loop
# seguia: stage obrigatório só parava com `stop_on_error`, o degradável virava
# `degraded` e o próximo começava. O hard limit (3600s) matava o worker no meio do
# stage seguinte. Sem `on_failure` e com o ack do Celery, o run ficava `running`
# até o watchdog flipá-lo para `heartbeat_timeout` 15 min depois.
#
# A composição é a de `run_pipeline_task`: `_execute_stages_loop` →
# `get_pipeline_client()` → `_run_stage` → runner. Só a folha é trocada, e o prazo
# corre num relógio falso que a própria folha adianta (ADR-446).

from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

import httpx
import pytest
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select

from backend.app.models.pipeline_run import (
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.services.pipeline import pipeline_client as pc
from backend.tests.test_stage_degradation import (  # noqa: F401 — `seeded` é fixture
    _E5_KEY,
    _E5_PAYLOAD,
    _reports,
    _run_row,
    _stage_log_count,
    _stage_status,
    seeded,
)
from pipeline.run_deadline import RunDeadline

_RECONCILE = "reconcile_transactions"
_CATEGORIZE = "categorize_transactions"
_E5 = "analyze_finances"
_NARRATIVAS = "generate_narratives"
_CROSSVAL = "validate_cross"
_PARECER = "review_finances_holistic"
_TAIL = [_NARRATIVAS, _CROSSVAL, _PARECER]

# Muito além do orçamento do relógio falso: quem "demora" estoura o prazo.
_LATE_S = 10_000.0


class _Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


@pytest.fixture
def in_process_run_stage_fn(monkeypatch, seeded):
    """O `_exec_stage` de `run_pipeline_task`, com o client que o deploy atual resolve."""
    monkeypatch.delenv("MATHOMS_PIPELINE_SERVICE_URL", raising=False)
    pc.reset_pipeline_client()
    client = pc.get_pipeline_client()
    assert isinstance(client, pc.InProcessPipelineClient)
    yield lambda c, s: client.execute_stage(c, s, workspace_id=seeded["ws_id"])
    pc.reset_pipeline_client()


def _behave(behaviour: str, ctx, clock: _Clock):
    """O que a folha faz: ``signal`` levanta; ``late_*`` adianta o relógio além do prazo."""
    if behaviour == "signal":
        raise SoftTimeLimitExceeded()
    if behaviour.startswith("late"):
        clock.now += _LATE_S
    if "e5" in behaviour:
        ctx.artifact_store.write(_E5, _E5_KEY, dict(_E5_PAYLOAD))
    if behaviour.endswith("fail"):
        return {"success": False}
    if behaviour.endswith("review"):
        return {"validation": {"valid": False, "errors": ["[CV3] conservação"]}}
    return {"ok": True}


def _install_leaves(monkeypatch, clock: _Clock, script: dict[str, str]) -> Counter:
    """Troca só os runners: o `_run_stage` real continua no meio da composição."""
    import pipeline.orchestrator as orchestrator

    calls: Counter = Counter()

    def _leaf_for(stage: str):
        def _runner(ctx):
            calls[stage] += 1
            return _behave(script.get(stage, "ok"), ctx, clock)

        return _runner

    monkeypatch.setattr(orchestrator, "_get_stage_runner", _leaf_for)
    return calls


def _drive(seed, run_stage_fn, *, stages, clock=None):
    """Loop + finalize de `run_pipeline_task`; `stop_on_error=False` prova que a parada não depende dele."""
    from backend.app.tasks.pipeline_task import _execute_stages_loop, _finalize_pipeline_outcome

    ids = {"run_id": seed["run_id"], "ws_id": seed["ws_id"]}
    ctx = SimpleNamespace(
        artifact_store=None, root=seed["tmp_path"], pipeline_run_id=ids["run_id"], config_dir=None
    )
    has_failure, paused = _execute_stages_loop(
        ctx,
        stages=stages,
        skip_llm=False,
        stop_on_error=False,
        tier="premium",
        llm_stages=set(),
        run_stage_fn=run_stage_fn,
        run_deadline=RunDeadline.starting_now(100, clock=clock) if clock else None,
        **ids,
    )
    _finalize_pipeline_outcome(*ids.values(), seed["tmp_path"], has_failure, paused)


async def _stage_log(seed, stage: str) -> PipelineStageLog:
    async with seed["async_session"]() as s:
        query = select(PipelineStageLog).where(
            PipelineStageLog.pipeline_run_id == seed["run_id"], PipelineStageLog.stage == stage
        )
        return (await s.execute(query)).scalar_one()


async def _assert_cut_by_time_limit(seed, stage: str, status, *, not_started: bool) -> None:
    log = await _stage_log(seed, stage)
    assert log.status is status
    assert log.output_summary["reason_class"] == "timeout"
    assert log.output_summary["time_limit"]["not_started"] is not_started
    assert (log.duration_ms is None) is not_started
    assert "tempo limite" in log.errors


@pytest.mark.asyncio
async def test_sinal_em_stage_obrigatorio_encerra_o_run_sem_iniciar_o_proximo(
    seeded, in_process_run_stage_fn, monkeypatch, clock
):
    calls = _install_leaves(monkeypatch, clock, {_RECONCILE: "signal"})

    _drive(seeded, in_process_run_stage_fn, stages=[_RECONCILE, _CATEGORIZE])

    assert calls == Counter({_RECONCILE: 1})
    assert await _stage_log_count(seeded, _CATEGORIZE) == 0
    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.failed
    assert run.failure_reason == "time_limit_exceeded"
    assert run.failed_at_stage == _RECONCILE
    assert run.current_stage is None and run.completed_at is not None
    await _assert_cut_by_time_limit(
        seeded, _RECONCILE, PipelineStageStatus.failed, not_started=False
    )


def _http_run_stage_fn(seed, posts: list[str]):
    """Executor do shell Go: o sinal estoura no read do httpx, fora de `_run_stage`."""

    def _handler(request: httpx.Request) -> httpx.Response:
        posts.append(request.url.path.rsplit("/", 2)[-2])
        raise SoftTimeLimitExceeded()

    client = pc.HttpPipelineClient(
        "http://shell", http=httpx.Client(transport=httpx.MockTransport(_handler))
    )
    return lambda c, s: client.execute_stage(c, s, workspace_id=seed["ws_id"])


@pytest.mark.asyncio
async def test_sinal_no_read_do_shell_encerra_o_run_sem_postar_o_proximo(seeded):
    posts: list[str] = []

    _drive(seeded, _http_run_stage_fn(seeded, posts), stages=[_RECONCILE, _CATEGORIZE])

    assert posts == [_RECONCILE]
    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.failed
    assert run.failure_reason == "time_limit_exceeded"
    assert run.failed_at_stage == _RECONCILE


@pytest.mark.asyncio
async def test_prazo_na_fronteira_antes_de_obrigatorio_registra_so_o_primeiro_nao_iniciado(
    seeded, in_process_run_stage_fn, monkeypatch, clock
):
    """O stage entregou, mas o prazo venceu nele: o próximo não começa."""
    calls = _install_leaves(monkeypatch, clock, {_RECONCILE: "late_ok"})

    _drive(seeded, in_process_run_stage_fn, stages=[_RECONCILE, _CATEGORIZE, _E5], clock=clock)

    assert calls == Counter({_RECONCILE: 1})
    assert await _stage_status(seeded, _RECONCILE) is PipelineStageStatus.completed
    await _assert_cut_by_time_limit(
        seeded, _CATEGORIZE, PipelineStageStatus.failed, not_started=True
    )
    assert await _stage_log_count(seeded, _E5) == 0
    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.failed
    assert (run.failure_reason, run.failed_at_stage) == ("time_limit_exceeded", _CATEGORIZE)


@pytest.mark.asyncio
async def test_sinal_em_degradavel_com_e5_entrega_relatorio_parcial(
    seeded, in_process_run_stage_fn, monkeypatch, clock
):
    """O caso que parar com `failed` perderia: o E5 existe, então o run entrega com lacuna."""
    calls = _install_leaves(monkeypatch, clock, {_E5: "e5", _NARRATIVAS: "signal"})

    _drive(seeded, in_process_run_stage_fn, stages=[_E5, *_TAIL])

    assert calls == Counter({_E5: 1, _NARRATIVAS: 1})
    degraded = PipelineStageStatus.degraded
    await _assert_cut_by_time_limit(seeded, _NARRATIVAS, degraded, not_started=False)
    for stage in (_CROSSVAL, _PARECER):
        await _assert_cut_by_time_limit(seeded, stage, degraded, not_started=True)
    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.partial_failure
    # ADR-357 §3: campo de falha nunca ao lado de status entregue.
    assert run.failure_reason is None and run.failed_at_stage is None
    assert len(await _reports(seeded)) == 1


@pytest.mark.asyncio
async def test_prazo_na_fronteira_depois_do_e5_degrada_a_cauda_inteira(
    seeded, in_process_run_stage_fn, monkeypatch, clock
):
    calls = _install_leaves(monkeypatch, clock, {_E5: "late_e5"})

    _drive(seeded, in_process_run_stage_fn, stages=[_E5, *_TAIL], clock=clock)

    assert calls == Counter({_E5: 1})
    for stage in _TAIL:
        await _assert_cut_by_time_limit(
            seeded, stage, PipelineStageStatus.degraded, not_started=True
        )
    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.partial_failure
    assert run.failure_reason is None
    assert len(await _reports(seeded)) == 1


@pytest.mark.asyncio
async def test_stage_que_engoliu_o_sinal_e_nao_entregou_carrega_timeout_e_o_motivo(
    seeded, in_process_run_stage_fn, monkeypatch, clock
):
    """O laço de retry do LLM engole o sinal: o stage volta sem entregar, depois do prazo."""
    calls = _install_leaves(monkeypatch, clock, {_RECONCILE: "late_fail"})

    _drive(seeded, in_process_run_stage_fn, stages=[_RECONCILE, _CATEGORIZE], clock=clock)

    assert calls == Counter({_RECONCILE: 1})
    log = await _stage_log(seeded, _RECONCILE)
    assert log.status is PipelineStageStatus.failed
    assert log.output_summary["reason_class"] == "timeout"
    # Run que já falhou não ganha "Falhou" em etapa que nunca rodou.
    assert await _stage_log_count(seeded, _CATEGORIZE) == 0
    run = await _run_row(seeded)
    assert (run.status, run.failure_reason) == (PipelineRunStatus.failed, "time_limit_exceeded")


@pytest.mark.asyncio
async def test_needs_review_entregue_vence_o_prazo(
    seeded, in_process_run_stage_fn, monkeypatch, clock
):
    calls = _install_leaves(monkeypatch, clock, {_RECONCILE: "late_review"})

    _drive(seeded, in_process_run_stage_fn, stages=[_RECONCILE, _CATEGORIZE], clock=clock)

    assert calls == Counter({_RECONCILE: 1})
    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.needs_review
    assert run.failure_reason is None


@pytest.mark.asyncio
async def test_falha_anterior_por_outra_causa_mantem_o_motivo_do_run(
    seeded, in_process_run_stage_fn, monkeypatch, clock
):
    """`failure_reason` nomeia a PRIMEIRA falha: o prazo que chega depois não a sobrescreve."""
    _install_leaves(monkeypatch, clock, {_RECONCILE: "fail", _CATEGORIZE: "signal"})

    _drive(seeded, in_process_run_stage_fn, stages=[_RECONCILE, _CATEGORIZE])

    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.failed
    assert run.failure_reason is None
    await _assert_cut_by_time_limit(
        seeded, _CATEGORIZE, PipelineStageStatus.failed, not_started=False
    )


@pytest.mark.asyncio
async def test_corte_no_ultimo_stage_depois_de_falha_anterior_fecha_o_run(
    seeded, in_process_run_stage_fn, monkeypatch, clock
):
    """Regressão: o corte do último stage não deixa resto, e o run já tinha falhado."""
    _install_leaves(monkeypatch, clock, {_RECONCILE: "fail", _PARECER: "signal"})

    _drive(seeded, in_process_run_stage_fn, stages=[_RECONCILE, _PARECER])

    run = await _run_row(seeded)
    assert (run.status, run.failure_reason) == (PipelineRunStatus.failed, None)
    await _assert_cut_by_time_limit(
        seeded, _PARECER, PipelineStageStatus.degraded, not_started=False
    )


@pytest.mark.asyncio
async def test_evento_de_prazo_sai_uma_vez_por_run(
    seeded, in_process_run_stage_fn, monkeypatch, clock
):
    import backend.app.tasks.pipeline_task as task_module

    events: list = []
    monkeypatch.setattr(
        task_module, "_log_run_time_limit", lambda limit, tier: events.append(limit)
    )
    _install_leaves(monkeypatch, clock, {_E5: "e5", _NARRATIVAS: "signal"})

    _drive(seeded, in_process_run_stage_fn, stages=[_E5, *_TAIL])

    assert [(e.stage, e.detection, e.caused_failure) for e in events] == [
        (_NARRATIVAS, "signal", False)
    ]


@pytest.mark.asyncio
async def test_on_failure_reconhece_o_sinal_que_escapou_do_loop(seeded):
    """Último recurso: o sinal estourou fora do loop (entre stages) e a task crashou."""
    from backend.app.tasks.pipeline_task import _on_pipeline_task_failure

    kwargs = {"run_id": seeded["run_id"]}
    _on_pipeline_task_failure(None, SoftTimeLimitExceeded(), "tid", (), kwargs, None)

    run = await _run_row(seeded)
    assert (run.status, run.failure_reason) == (PipelineRunStatus.failed, "time_limit_exceeded")


def test_prazo_nasce_do_soft_limit_efetivo_da_task():
    """Override por chamada (`request.timelimit`) vence o default da task; a carência vem depois."""
    from backend.app.tasks.pipeline_task import _run_deadline_for
    from pipeline.run_deadline import SIGNAL_GRACE_S

    default = SimpleNamespace(request=SimpleNamespace(timelimit=None), soft_time_limit=3000)
    override = SimpleNamespace(request=SimpleNamespace(timelimit=(700, 600)), soft_time_limit=3000)

    assert _run_deadline_for(default).budget_s == 3000
    deadline = _run_deadline_for(override)
    assert deadline.budget_s == 600
    assert deadline.expires_at - deadline.started_at == pytest.approx(600 + SIGNAL_GRACE_S)
    no_limit = SimpleNamespace(request=SimpleNamespace(timelimit=None), soft_time_limit=None)
    assert _run_deadline_for(no_limit).expires_at is None


_TASK_NOOPS = (
    "_materialize_tarefas_md",
    "_finalize_pipeline_outcome",
    "_flush_deferred_llm_call_log",
)


def _stub_task_internals(monkeypatch, seen: dict) -> None:
    """Tudo em volta do prazo vira no-op; o que sobra é a fiação dele."""
    import backend.app.tasks.pipeline_task as task_module

    def _setup(*_args, run_deadline, **_kwargs):
        seen["hooks"] = run_deadline
        return SimpleNamespace(base_run_id=None, base_run_fallback_stages=frozenset()), None

    def _loop(*_args, run_deadline, **_kwargs):
        seen["loop"] = run_deadline
        return False, False

    monkeypatch.setattr(task_module, "_setup_run_context", _setup)
    monkeypatch.setattr(task_module, "_execute_stages_loop", _loop)
    monkeypatch.setattr(task_module, "_mark_run_started", lambda *_a: True)
    for name in _TASK_NOOPS:
        monkeypatch.setattr(task_module, name, lambda *_a: None)


def test_run_pipeline_task_entrega_o_mesmo_prazo_aos_hooks_e_ao_loop(monkeypatch, tmp_path):
    """Um prazo só por run: o que os hooks do LLM consultam é o que o loop consulta."""
    from backend.app.tasks.pipeline_task import run_pipeline_task

    seen: dict = {}
    _stub_task_internals(monkeypatch, seen)

    run_pipeline_task.run(
        "run",
        "ws",
        str(tmp_path),
        str(tmp_path),
        ["reconcile_transactions"],
        True,
        True,
        incremental=True,
    )

    assert seen["hooks"] is seen["loop"]
    assert seen["loop"].budget_s == run_pipeline_task.soft_time_limit
