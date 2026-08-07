"""Degradação de stage no card de `/admin/metrics` (A40.l18 · §Decisões do dono, 2)."""

# O dono recusou explicitamente "só log estruturado": é o mesmo modo de falha que
# produziu o incidente de origem (ADR-304 §Emenda — 16 itens apagados em 7 runs,
# 9 dias sem detecção). Log sem sink é silêncio com outra sintaxe.
#
# **Zeros estruturais, não `dict[str, int]`.** Status ou `reason_class` ausentes da
# janela não produzem row no `group_by`; sem zero-fill sobre TODO o enum, zero e
# ausência ficam indistinguíveis na tela — exatamente o silêncio recusado. O
# zero-fill é sobre os membros do enum, não sobre o que a query devolveu.
#
# **Agregação em Python para `reason_class`.** Ele vive dentro do JSON de
# `output_summary`. Query JSON-path é portável, mas seria a PRIMEIRA do repo e a
# suíte de PR roda só SQLite — query nova validada no dialeto errado é falso-verde.
# Volume é minúsculo (stages degradados numa janela de 30 dias). Revisitar quando:
# Postgres vivo E rows degradadas na casa dos milhares, OU p95 do endpoint
# encostando no 1s do SLO.md.

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.services.pipeline.stage_failure_reason import StageFailureReason


async def runs_by_status(db: AsyncSession, *, cutoff: datetime) -> dict[str, int]:
    """Contagem por status na janela, ancorada em `PipelineRun.started_at`."""
    # Mesma âncora de `pipeline_runs_last_period`, e é isso que dá o invariante de
    # graça: a soma deste dict fecha com aquele número. Dois números adjacentes no
    # mesmo card que não fecham é bug de confiança.
    rows = await db.execute(
        select(PipelineRun.status, func.count())
        .where(PipelineRun.started_at >= cutoff)
        .group_by(PipelineRun.status)
    )
    # `group_by` sobre coluna `Enum(PyEnum)` devolve MEMBROS do enum, não strings:
    # sem `.value` a chave não serializa.
    counted = {status.value: int(n) for status, n in rows.all()}
    return {member.value: counted.get(member.value, 0) for member in PipelineRunStatus}


async def degraded_stages(
    db: AsyncSession, *, cutoff: datetime
) -> tuple[dict[str, int], dict[str, int]]:
    """`(por reason_class, por stage)` dos stages degradados na janela."""
    # Âncora em `PipelineStageLog.started_at` (tabela própria, sem join com
    # janela): a pergunta do dono é "degradou quando?". NÃO reconcilia com
    # `runs_by_status` — N stages por run, e run longo cruza a janela — e é por
    # isso que o rótulo do card precisa dizer "stages que degradaram na janela".
    rows = await db.execute(
        select(PipelineStageLog.stage, PipelineStageLog.output_summary).where(
            PipelineStageLog.status == PipelineStageStatus.degraded,
            PipelineStageLog.started_at >= cutoff,
        )
    )
    return _tally(rows.all())


def _tally(rows) -> tuple[dict[str, int], dict[str, int]]:
    by_reason = {member.value: 0 for member in StageFailureReason}
    by_stage: dict[str, int] = {}
    for stage, summary in rows:
        reason = _reason_of(summary)
        by_reason[reason] = by_reason.get(reason, 0) + 1
        by_stage[stage] = by_stage.get(stage, 0) + 1
    return by_reason, by_stage


def _reason_of(summary) -> str:
    """`unknown` para row sem a chave — rows legadas e o caso "não classificado"."""
    if not isinstance(summary, dict):
        return StageFailureReason.unknown.value
    reason = summary.get("reason_class")
    valid = {m.value for m in StageFailureReason}
    return (
        reason if isinstance(reason, str) and reason in valid else StageFailureReason.unknown.value
    )


def cutoff_for(period_days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=period_days)
