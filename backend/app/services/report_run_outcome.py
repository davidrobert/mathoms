"""Desfecho do run que gerou o relatório, na forma que a tela precisa (A40.l18 · ADR-357)."""

# O consumidor é o `ReportDataQualityBanner`: ele hoje AFIRMA "sem pendências que
# afetem a leitura deste relatório", e essa afirmação sai no PDF que circula com
# cônjuge e contador. Num run degradado ela é falsa.
#
# **Polaridade positiva de propósito.** O predicado é "o run entregou tudo que ia
# entregar?", não "o run degradou?". O negativo (`status == partial_failure ⇒
# suprime`) deixaria o relatório de um run **cancelado** — que já é gerado hoje,
# quando o cancel vem depois de `analyze_finances` — ainda afirmando que está
# limpo. Positivo cobre cancelado, `failed` com E5 e qualquer status futuro de
# graça.
#
# `unknown` é membro explícito, nunca ausência: `reports.pipeline_run_id` é
# `ondelete="SET NULL"`, e um campo opcional que chega `undefined` faria a
# supressão sumir em silêncio no rollout.

from __future__ import annotations

import enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)


class ReportRunOutcome(str, enum.Enum):
    """Desfecho do run sob a ótica do relatório."""

    complete = "complete"
    with_gap = "with_gap"
    unknown = "unknown"


async def _statuses_for(db: AsyncSession, ids: list[str]) -> dict[str, PipelineRunStatus]:
    rows = await db.execute(
        select(PipelineRun.id, PipelineRun.status).where(PipelineRun.id.in_(ids))
    )
    return dict(rows.all())


async def _runs_with_degraded_stage(db: AsyncSession, ids: list[str]) -> set[str]:
    rows = await db.execute(
        select(PipelineStageLog.pipeline_run_id).where(
            PipelineStageLog.pipeline_run_id.in_(ids),
            PipelineStageLog.status == PipelineStageStatus.degraded,
        )
    )
    return set(rows.scalars().all())


async def run_outcomes_for(db: AsyncSession, run_ids: list[str]) -> dict[str, ReportRunOutcome]:
    """Desfecho por `run_id`, em 2 queries — nunca uma por relatório."""
    ids = [r for r in run_ids if r]
    if not ids:
        return {}
    statuses = await _statuses_for(db, ids)
    degraded = await _runs_with_degraded_stage(db, ids)
    return {rid: _outcome(statuses.get(rid), rid in degraded) for rid in ids}


def _outcome(status: PipelineRunStatus | None, has_degraded_stage: bool) -> ReportRunOutcome:
    if status is None:
        return ReportRunOutcome.unknown
    if status is PipelineRunStatus.completed and not has_degraded_stage:
        return ReportRunOutcome.complete
    return ReportRunOutcome.with_gap


def outcome_for_report(run_id: str | None, outcomes: dict[str, ReportRunOutcome]):
    """`unknown` quando o run foi purgado (FK `SET NULL`) — nunca ausência de campo."""
    if not run_id:
        return ReportRunOutcome.unknown
    return outcomes.get(run_id, ReportRunOutcome.unknown)
