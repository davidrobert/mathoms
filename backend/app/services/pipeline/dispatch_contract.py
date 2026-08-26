"""Contrato de ciclo de vida de um run: quem precede o executor e como cada estado sai (ADR-359 · ADR-417)."""

# Existe para que o predicado de órfão pare de ser o literal ``pending`` espalhado. Havia
# QUATRO lugares independentes decidindo "quem ainda não tem dono", e `resuming` — nascido
# depois — não entrou em nenhum: `fin.detect_stuck_runs` filtra `running`,
# `_check_no_active_run` e `_heal_undispatched_run` filtram `pending`, e a guarda do cancel
# (duplicada em `cancel_run` e `cancel_pipeline_run`) aceitava só `pending`/`running`.
# Resultado medido: órfão em `resuming` era o **único estado inescapável do sistema** — não
# bloqueava (fora do índice parcial `ux_pipeline_runs_ws_active`) e nunca morria.

from __future__ import annotations

import os
from datetime import timedelta
from enum import Enum

from backend.app.models.pipeline_run import PipelineRunStatus

_THRESHOLD_ENV = "MATHOMS_UNDISPATCHED_RUN_THRESHOLD_MINUTES"

#: 2min, NÃO os 15min da ADR-172: aquele número calibra *stage genuinamente lento*,
#: semântica que aqui não existe — entre o INSERT e o enqueue não há trabalho a esperar.
#: Detecção worst-case = período do beat (300s) + este threshold.
DEFAULT_UNDISPATCHED_THRESHOLD_MINUTES = 2


# Fonte única para as DUAS portas — a cura síncrona no trigger e a varredura de beat.
# Duplicar a leitura do env deixaria as portas divergirem sob override.
def undispatched_threshold() -> timedelta:
    """Janela de graça antes de declarar um run sem dono."""
    raw = os.environ.get(_THRESHOLD_ENV)
    try:
        minutes = int(raw) if raw else DEFAULT_UNDISPATCHED_THRESHOLD_MINUTES
    except ValueError:
        minutes = DEFAULT_UNDISPATCHED_THRESHOLD_MINUTES
    return timedelta(minutes=max(minutes, 1))


#: Estados não-terminais em que a linha existe e **nenhum executor foi confirmado**.
#: `pending` nasce assim no trigger; `resuming` nasce assim no resume. Ambos passam por
#: `_dispatch_celery_task`, que grava `celery_task_id` ANTES do enqueue — logo o
#: discriminante de órfão (`celery_task_id IS NULL`) é uniforme nos dois.
PRE_DISPATCH_STATUSES: tuple[PipelineRunStatus, ...] = (
    PipelineRunStatus.pending,
    PipelineRunStatus.resuming,
)

#: Estados terminais: o run acabou e nenhum executor pode re-entrar. Fonte única —
#: `pipeline_task` importa daqui em vez de manter a própria cópia, que era o quinto
#: lugar decidindo sozinho sobre o ciclo de vida do run.
TERMINAL_STATUSES: tuple[PipelineRunStatus, ...] = (
    PipelineRunStatus.completed,
    PipelineRunStatus.failed,
    PipelineRunStatus.partial_failure,
    PipelineRunStatus.cancelled,
)

#: Estados que `cancel_pipeline_run` aceita. `resuming` entra porque o zumbi tem de ter
#: uma porta de saída manual (A40.l27); `needs_review` entra pelo mesmo motivo
#: (ADR-417 D1) — a versão anterior desta constante o excluía dizendo que
#: "cancelá-la é decisão de produto, não de operação", mas a decisão de produto já
#: estava tomada desde 2026-04-21: `NeedsReviewCard` oferece o botão e recebia 409. E a
#: exclusão não protegia de varredura nenhuma — `detect_stuck_runs` filtra `running` e
#: `_heal_undispatched_run` filtra pre-dispatch; quem chama `cancel` é humano
#: autenticado atrás de `require_write_role`.
CANCELLABLE_STATUSES: tuple[PipelineRunStatus, ...] = (
    PipelineRunStatus.pending,
    PipelineRunStatus.running,
    PipelineRunStatus.resuming,
    PipelineRunStatus.needs_review,
)


class RunExit(str, Enum):
    """Como um estado de run sai de si mesmo."""

    terminal = "terminal"
    manual_cancel = "manual_cancel"
    sweep_undispatched = "sweep_undispatched"
    sweep_heartbeat = "sweep_heartbeat"


#: ADR-417 D7 — a saída de CADA estado, declarada. Existe porque duas vezes um estado
#: nasceu sem porta e ninguém notou até virar incidente: `resuming` (A40.l27) e
#: `needs_review` (A40.l87). Membro novo do enum falha o gate **por ausência** aqui, o que
#: obriga o autor a escrever "a saída deste estado é X" — reflexão que nenhum dos dois
#: recebeu. Gate: `test_dispatch_contract.py`.
RUN_EXIT_BY_STATUS: dict[PipelineRunStatus, tuple[RunExit, ...]] = {
    PipelineRunStatus.completed: (RunExit.terminal,),
    PipelineRunStatus.failed: (RunExit.terminal,),
    PipelineRunStatus.partial_failure: (RunExit.terminal,),
    PipelineRunStatus.cancelled: (RunExit.terminal,),
    PipelineRunStatus.pending: (RunExit.manual_cancel, RunExit.sweep_undispatched),
    PipelineRunStatus.resuming: (RunExit.manual_cancel, RunExit.sweep_undispatched),
    PipelineRunStatus.running: (RunExit.manual_cancel, RunExit.sweep_heartbeat),
    # Sem varredura de propósito: a pausa espera uma pessoa, e expirá-la por tempo
    # descartaria trabalho que o usuário ainda pretende conferir.
    PipelineRunStatus.needs_review: (RunExit.manual_cancel,),
}


def discarded_at_review(status: PipelineRunStatus | str, paused_at_stage: str | None) -> bool:
    """Run descartado numa pausa, e não interrompido em execução (ADR-417 D4).

    Derivado, não persistido: `cancel_pipeline_run` grava só `status` e `completed_at`,
    então `paused_at_stage` sobrevive ao cancelamento e o par discrimina sozinho. Uma
    coluna nova registraria o *porquê* sem o *quem* — e `failure_reason` faria abandono
    deliberado contar em métrica de confiabilidade.
    """
    return status == PipelineRunStatus.cancelled and bool(paused_at_stage)


__all__ = [
    "CANCELLABLE_STATUSES",
    "DEFAULT_UNDISPATCHED_THRESHOLD_MINUTES",
    "PRE_DISPATCH_STATUSES",
    "RUN_EXIT_BY_STATUS",
    "RunExit",
    "TERMINAL_STATUSES",
    "discarded_at_review",
    "undispatched_threshold",
]
