"""Revisão do executor (ADR-362) do stage E5 do run que gerou o relatório."""

# O consumidor é o colofão do relatório (`ReportSourceStrip`): proveniência de
# "que código computou estes números", ao lado de "Execução". O relatório É o
# output de `analyze_finances` — por isso a revisão exposta é a desse stage,
# não a do run inteiro: um run com resume pode atravessar deploys e carregar
# N revisões distintas nos stage logs.
#
# `None` é valor legítimo (executor não declarou: run pré-ADR-362, dev sem
# MATHOMS_BUILD_SHA, run purgado) — a UI renderiza "—", nunca fabrica valor.
# Vale a mesma regra da ADR-362: nunca backfill.

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import PipelineStageLog

# Só o nome descritivo — e o par legado NÃO é omissão. A coluna nasceu em
# 2026-08 (ADR-362) e todo writer emite nome descritivo desde F9.6 (2026-07-06),
# então um row de stage legado tem `executor_revision` NULL por construção:
# consultá-lo devolveria o mesmo `None` que ignorá-lo. Medido no DB de dogfood
# em 2026-08-11: 0 rows de stage legado, 77 descritivos.
_ANALYSIS_STAGE = "analyze_finances"


async def analysis_revisions_for(
    db: AsyncSession, run_ids: list[str | None]
) -> dict[str, str | None]:
    """Revisão do stage E5 mais recente por `run_id`, em 1 query — nunca uma por relatório."""
    ids = [r for r in run_ids if r]
    if not ids:
        return {}
    rows = await db.execute(
        select(
            PipelineStageLog.pipeline_run_id,
            PipelineStageLog.executor_revision,
            PipelineStageLog.started_at,
        ).where(
            PipelineStageLog.pipeline_run_id.in_(ids),
            PipelineStageLog.stage == _ANALYSIS_STAGE,
        )
    )
    latest = _latest_revision_by_run(rows.all())
    return {rid: latest.get(rid) for rid in ids}


def _latest_revision_by_run(rows: list) -> dict[str, str | None]:
    latest: dict[str, tuple] = {}
    for run_id, revision, started_at in rows:
        current = latest.get(run_id)
        if current is None or started_at > current[0]:
            latest[run_id] = (started_at, revision)
    return {rid: revision for rid, (_, revision) in latest.items()}


def revision_for_report(run_id: str | None, revisions: dict[str, str | None]) -> str | None:
    """`None` quando o run foi purgado (FK `SET NULL`) ou nunca logou E5."""
    if not run_id:
        return None
    return revisions.get(run_id)
