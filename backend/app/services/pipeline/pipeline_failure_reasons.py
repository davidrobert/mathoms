"""Vocabulário aberto de ``PipelineRun.failure_reason`` (ADR-172, W2-T04)."""

from __future__ import annotations

#: Beat task ``fin.detect_stuck_runs`` flagou run com heartbeat estale.
HEARTBEAT_TIMEOUT = "heartbeat_timeout"

#: ADR-359 — o broker recusou o enqueue; a compensação síncrona marcou o run.
#: Sabemos *que* falhou e o usuário recebeu 503.
DISPATCH_FAILED = "dispatch_failed"

#: ADR-359 — ``_prepare_run_context`` falhou (materialização de config /
#: storage) antes de qualquer tentativa de enqueue. Porta distinta, mesma
#: classe de órfão.
RUN_SETUP_FAILED = "run_setup_failed"

#: ADR-359 — varredura encontrou run pendente que ninguém reivindicou e que
#: nunca chegou a gravar ``celery_task_id``. Só sabemos que não há dono
#: (provável morte do processo entre o INSERT e o dispatch) — investigação e
#: ação de runbook diferentes de ``DISPATCH_FAILED``, daí o nome próprio.
DISPATCH_UNCONFIRMED = "dispatch_unconfirmed"

ALL_REASONS: frozenset[str] = frozenset(
    {HEARTBEAT_TIMEOUT, DISPATCH_FAILED, RUN_SETUP_FAILED, DISPATCH_UNCONFIRMED}
)
