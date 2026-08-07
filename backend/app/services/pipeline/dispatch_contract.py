"""Contrato de dispatch de um run: quais estados precedem o executor (ADR-359 · A40.l27)."""

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

#: Estados que `cancel_pipeline_run` aceita. `resuming` entra porque o zumbi tem de ter
#: uma porta de saída manual; `needs_review` fica fora de propósito — pausa é estado
#: legítimo e cancelá-la é decisão de produto, não de operação.
CANCELLABLE_STATUSES: tuple[PipelineRunStatus, ...] = (
    PipelineRunStatus.pending,
    PipelineRunStatus.running,
    PipelineRunStatus.resuming,
)

__all__ = [
    "CANCELLABLE_STATUSES",
    "DEFAULT_UNDISPATCHED_THRESHOLD_MINUTES",
    "PRE_DISPATCH_STATUSES",
    "undispatched_threshold",
]
