"""A40.l27 — varredura ``fin.detect_undispatched_runs`` + cancel de ``resuming``.

O órfão em `resuming` era o **único estado inescapável do sistema**: fora do predicado de
`fin.detect_stuck_runs` (que filtra `running`), com `celery_task_id` stale não-NULL (logo
invisível ao discriminante de órfão), recusado por `cancel_pipeline_run` e devolvendo
`is_run_active is True` para sempre. Não bloqueava e nunca morria.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.services.pipeline.dispatch_contract import (
    CANCELLABLE_STATUSES,
    PRE_DISPATCH_STATUSES,
)
from backend.app.services.pipeline.pipeline_failure_reasons import (
    DISPATCH_FAILED,
    DISPATCH_UNCONFIRMED,
)
from backend.app.tasks.periodic_tasks import _PRE_DISPATCH_CLOCK, detect_undispatched_runs
from backend.tests.factories.builders import make_user, make_workspace

_LONG_AGO = timedelta(hours=1)
_RECENT = timedelta(seconds=5)


# `started_at` e `last_heartbeat_at` recebem a MESMA idade — a varredura escolhe o relógio
# por status (`_PRE_DISPATCH_CLOCK`).
async def _make_run(
    db: AsyncSession,
    *,
    status: PipelineRunStatus,
    celery_task_id: str | None,
    age: timedelta = _LONG_AGO,
) -> PipelineRun:
    """Run pré-dispatch com idade e dono controlados."""
    stamp = datetime.now(timezone.utc) - age
    return await _insert(db, status=status, celery_task_id=celery_task_id, clocks=(stamp, stamp))


async def _insert(
    db: AsyncSession,
    *,
    status: PipelineRunStatus,
    celery_task_id: str | None,
    clocks: tuple[datetime, datetime | None],
) -> PipelineRun:
    """Insere o run com `(started_at, last_heartbeat_at)` explícitos e independentes."""
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = PipelineRun(
        workspace_id=ws.id,
        status=status,
        celery_task_id=celery_task_id,
        started_at=clocks[0],
        last_heartbeat_at=clocks[1],
    )
    db.add(run)
    await db.commit()
    return run


async def _reload(db: AsyncSession, run_id: str) -> PipelineRun:
    return (
        await db.execute(
            select(PipelineRun)
            .where(PipelineRun.id == run_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


# Handler NO PRÓPRIO logger, não `caplog`. Medido: com a suíte inteira o `caplog` não via
# nada (`por_run == []`) porque algum módulo desliga `propagate` num ancestral e o handler
# do caplog vive no root — o teste passava sozinho e falhava em conjunto. `at_level(logger=)`
# não resolve: ele ajusta o nível, não move o handler.
class _Coletor(logging.Handler):
    """Handler que acumula os records em memória."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.registros: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.registros.append(record)


# `disabled = True` medido quando a suíte inteira roda: outro teste reconfigura logging e
# desliga os loggers já existentes. É poluição de TESTE, não risco de produção — não há
# `dictConfig`/`configure_logging` no caminho do app (verificado).
@contextmanager
def _capture_warnings():
    from backend.app.tasks import periodic_tasks

    logger, handler = periodic_tasks.logger, _Coletor()
    anterior = (logger.level, logger.disabled)
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    logger.disabled = False
    try:
        yield handler.registros
    finally:
        logger.removeHandler(handler)
        logger.setLevel(anterior[0])
        logger.disabled = anterior[1]


def _force_candidate(monkeypatch, run: PipelineRun) -> None:
    """Simula a lista do SELECT de um instante ANTERIOR: o objeto reflete o estado de
    então, e o UPDATE tem de reconciliar com o estado atual do DB."""
    from backend.app.tasks import periodic_tasks

    stale = PipelineRun(
        id=run.id,
        workspace_id=run.workspace_id,
        status=PipelineRunStatus.pending,
        celery_task_id=None,
    )
    monkeypatch.setattr(periodic_tasks, "_select_undispatched_candidates", lambda db_, now: [stale])


@pytest.fixture(autouse=True)
def _silence_publish(monkeypatch):
    monkeypatch.setattr(
        "backend.app.tasks.periodic_tasks.publish_run_failed", lambda *_a, **_k: None
    )


# -----------------------------------------------------------------------
# O invariante nº 1: a varredura não descarta trabalho legítimo
# -----------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("status", list(PRE_DISPATCH_STATUSES))
async def test_run_enfileirado_nunca_e_marcado_unconfirmed(
    db: AsyncSession, status: PipelineRunStatus
) -> None:
    """Fila funda: `celery_task_id` não-NULL e idade MUITO acima do threshold. É o que a
    pré-geração do task_id (ADR-359 §4) compra — sem este teste a varredura mataria run
    legítimo esperando worker."""
    run = await _make_run(db, status=status, celery_task_id="task-enfileirado")

    assert detect_undispatched_runs.run() == {"reaped": 0}

    refreshed = await _reload(db, run.id)
    assert refreshed.status == status
    assert refreshed.failure_reason is None


@pytest.mark.asyncio
async def test_run_dentro_do_threshold_nao_e_colhido(db: AsyncSession) -> None:
    """Threshold é a margem anti-corrida: run recém-inserido ainda vai ser despachado."""
    run = await _make_run(db, status=PipelineRunStatus.pending, celery_task_id=None, age=_RECENT)

    assert detect_undispatched_runs.run() == {"reaped": 0}
    assert (await _reload(db, run.id)).status == PipelineRunStatus.pending


# -----------------------------------------------------------------------
# O item grave: o órfão em `resuming`
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orfao_em_resuming_e_colhido_pela_varredura(db: AsyncSession) -> None:
    run = await _make_run(db, status=PipelineRunStatus.resuming, celery_task_id=None)

    assert detect_undispatched_runs.run() == {"reaped": 1}

    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.failed
    assert refreshed.failure_reason == DISPATCH_UNCONFIRMED
    assert refreshed.completed_at is not None


@pytest.mark.asyncio
async def test_orfao_em_resuming_e_cancelavel(db: AsyncSession) -> None:
    """O outro assert que a lane exige: o zumbi tem porta de saída manual. Antes,
    `cancel_pipeline_run` recusava tudo fora de `pending`/`running`."""
    from backend.app.services.pipeline.pipeline_service import cancel_pipeline_run

    run = await _make_run(db, status=PipelineRunStatus.resuming, celery_task_id=None)

    assert cancel_pipeline_run(run.id) is True
    assert (await _reload(db, run.id)).status == PipelineRunStatus.cancelled


@pytest.mark.asyncio
async def test_needs_review_nao_e_cancelavel_nem_colhido(db: AsyncSession) -> None:
    """Pausa é estado legítimo: nem a varredura nem o cancel a tocam. Alargar o
    predicado até aqui mataria run que só espera o usuário."""
    from backend.app.services.pipeline.pipeline_service import cancel_pipeline_run

    run = await _make_run(db, status=PipelineRunStatus.needs_review, celery_task_id=None)

    assert detect_undispatched_runs.run() == {"reaped": 0}
    assert cancel_pipeline_run(run.id) is False
    assert (await _reload(db, run.id)).status == PipelineRunStatus.needs_review


@pytest.mark.asyncio
async def test_pending_sem_dono_e_colhido(db: AsyncSession) -> None:
    run = await _make_run(db, status=PipelineRunStatus.pending, celery_task_id=None)

    assert detect_undispatched_runs.run() == {"reaped": 1}
    assert (await _reload(db, run.id)).failure_reason == DISPATCH_UNCONFIRMED


# -----------------------------------------------------------------------
# Vocabulário e contrato
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unconfirmed_nao_colapsa_com_dispatch_failed(db: AsyncSession) -> None:
    """A varredura emite `dispatch_unconfirmed`; `dispatch_failed` é a compensação
    síncrona. Colapsar os dois destrói o sinal de postmortem (ADR-359 §3)."""
    run = await _make_run(db, status=PipelineRunStatus.pending, celery_task_id=None)

    detect_undispatched_runs.run()

    assert (await _reload(db, run.id)).failure_reason != DISPATCH_FAILED


def test_todo_status_pre_dispatch_tem_relogio() -> None:
    """Status novo em `PRE_DISPATCH_STATUSES` sem entrada em `_PRE_DISPATCH_CLOCK` sairia
    da varredura em SILÊNCIO — o mesmo modo de falha que deixou `resuming` de fora."""
    assert set(_PRE_DISPATCH_CLOCK) == set(PRE_DISPATCH_STATUSES)


def test_cancelavel_cobre_os_pre_dispatch_mais_running() -> None:
    assert set(PRE_DISPATCH_STATUSES) <= set(CANCELLABLE_STATUSES)
    assert PipelineRunStatus.running in CANCELLABLE_STATUSES
    assert PipelineRunStatus.needs_review not in CANCELLABLE_STATUSES


# `WARNING` por run colhido (espelhando `_log_stuck_run`) **e** uma agregada com a
# contagem. Só a agregada obrigaria SQL para saber *qual run, qual workspace* — que é como
# `failure_reason` virou write-only por 3 meses. Nada em `CRITICAL`: sem pager (ADR-359 §7).
@pytest.mark.asyncio
async def test_log_por_run_mais_agregado(db: AsyncSession) -> None:
    """Duas linhas por-run + uma agregada, todas `WARNING`."""
    await _make_run(db, status=PipelineRunStatus.pending, celery_task_id=None)
    await _make_run(db, status=PipelineRunStatus.resuming, celery_task_id=None)

    with _capture_warnings() as registros:
        assert detect_undispatched_runs.run() == {"reaped": 2}

    por_run = [r for r in registros if r.__dict__.get("event", "").endswith("_run_reaped")]
    agregado = [r for r in registros if r.__dict__.get("event", "").endswith("_runs_reaped")]
    assert len(por_run) == 2
    assert {r.__dict__["failure_reason"] for r in por_run} == {DISPATCH_UNCONFIRMED}
    assert all(r.__dict__.get("run_id") for r in por_run)
    assert len(agregado) == 1
    assert agregado[0].__dict__["count"] == 2
    assert all(r.levelno == logging.WARNING for r in por_run + agregado)


# -----------------------------------------------------------------------
# Atomicidade — exercitada, não nomeada
# -----------------------------------------------------------------------


# O run entra na lista de candidatos e o dispatcher grava o `celery_task_id` ANTES do
# UPDATE. O filtro no próprio UPDATE tem de fazer `rowcount == 0` e o run sobreviver.
# Este teste existe porque a mutação provou que os demais passavam com UPDATE
# INCONDICIONAL — eles nomeavam a atomicidade sem exercitá-la.
@pytest.mark.asyncio
async def test_corrida_com_o_dispatcher_nao_mata_o_run(db: AsyncSession, monkeypatch) -> None:
    """Dispatcher ganha a corrida ⇒ o run legítimo sobrevive à varredura."""
    run = await _make_run(db, status=PipelineRunStatus.pending, celery_task_id="ganhou-a-corrida")
    _force_candidate(monkeypatch, run)

    assert detect_undispatched_runs.run() == {"reaped": 0}

    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.pending
    assert refreshed.failure_reason is None


@pytest.mark.asyncio
async def test_corrida_de_status_nao_mata_o_run(db: AsyncSession, monkeypatch) -> None:
    """Mesma corrida, pelo outro lado: o run já avançou para `running` (o worker o
    reivindicou). O filtro de status esperado no UPDATE protege."""
    run = await _make_run(db, status=PipelineRunStatus.running, celery_task_id=None)
    _force_candidate(monkeypatch, run)

    assert detect_undispatched_runs.run() == {"reaped": 0}
    assert (await _reload(db, run.id)).status == PipelineRunStatus.running


def _as_utc(value: datetime) -> datetime:
    """SQLite devolve `DateTime(timezone=True)` naive — normaliza antes de comparar."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


# Sem estes três writes o órfão de resume é INDETECTÁVEL: o `celery_task_id` herdado do run
# original faria o discriminante nunca casar, `started_at` (do original) faria o threshold
# ser vacuidade, e `paused_at_stage` zerado destruiria a única cópia durável da pausa.
async def _make_paused_run(db: AsyncSession, *, antes: datetime, stage: str) -> PipelineRun:
    """Run em `needs_review` com task_id do run ORIGINAL e relógios velhos."""
    run = await _insert(
        db,
        status=PipelineRunStatus.needs_review,
        celery_task_id="task-do-run-original",
        clocks=(antes, antes),
    )
    run.paused_at_stage = stage
    await db.commit()
    return run


@pytest.mark.asyncio
async def test_resume_limpa_o_task_id_stale_e_stampa_o_relogio(db: AsyncSession) -> None:
    """O flip para `resuming` deixa o estado auto-descritivo e diagnosticável."""
    from backend.app.services.pipeline import pipeline_service

    antes = datetime.now(timezone.utc) - _LONG_AGO
    run = await _make_paused_run(db, antes=antes, stage="analyze_finances")

    paused_stage, _tier = pipeline_service._flip_run_to_resuming(run.id, run.workspace_id)

    assert paused_stage == "analyze_finances"
    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.resuming
    assert refreshed.celery_task_id is None
    assert refreshed.paused_at_stage == "analyze_finances"  # PRESERVADO (co-design P3)
    assert _as_utc(refreshed.last_heartbeat_at) > antes


# -----------------------------------------------------------------------
# Os dois testes que o co-design nomeou como decisivos
# -----------------------------------------------------------------------


# Um resume legítimo pode ficar em `resuming` além do threshold enquanto
# `_prepare_run_context` materializa config/storage. Com `started_at` (do run ORIGINAL,
# horas antes) o predicado seria sempre verdadeiro: o reaper mataria o run, o `apply_async`
# seguinte enfileiraria, `_mark_run_started` recusaria por terminal, e o trabalho seria
# descartado em silêncio com `failure_reason` mentiroso — a alternativa que a ADR-359
# §Alternativas rejeitou nominalmente.
@pytest.mark.asyncio
async def test_resume_legitimo_lento_nao_e_colhido(db: AsyncSession) -> None:
    """O falso-positivo garantido em prod, se o relógio fosse `started_at`."""
    agora = datetime.now(timezone.utc)
    run = await _insert(
        db,
        status=PipelineRunStatus.resuming,
        celery_task_id=None,
        # run original MUITO velho, mas entrou em `resuming` AGORA
        clocks=(agora - _LONG_AGO, agora - _RECENT),
    )

    assert detect_undispatched_runs.run() == {"reaped": 0}
    assert (await _reload(db, run.id)).status == PipelineRunStatus.resuming


@pytest.mark.asyncio
async def test_orfao_pending_com_heartbeat_null_nao_levanta(db: AsyncSession) -> None:
    """Órfão que morreu entre o INSERT e o dispatch tem `last_heartbeat_at` NULL. O
    selector/flipper são próprios exatamente por isso — alargar `_flip_one_stuck` daria
    `TypeError` em `now - _as_utc(None)` na primeira execução."""
    run = await _insert(
        db,
        status=PipelineRunStatus.pending,
        celery_task_id=None,
        clocks=(datetime.now(timezone.utc) - _LONG_AGO, None),
    )

    assert detect_undispatched_runs.run() == {"reaped": 1}
    assert (await _reload(db, run.id)).failure_reason == DISPATCH_UNCONFIRMED
