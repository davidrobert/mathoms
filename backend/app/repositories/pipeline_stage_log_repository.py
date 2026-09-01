"""PipelineStageLogRepository — queries de leitura de ``pipeline_stage_logs``.

Uso primário (ADR-119): mediana de duração por stage para estimativa de
tempo honesta na UI. Query é agregada por-stage e filtra apenas runs
bem-sucedidos (status=completed) que de fato EXECUTARAM.
"""

from __future__ import annotations

import statistics

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineStageLog,
    PipelineStageStatus,
)

# ADR-119: só emitimos estimativa com amostra estatisticamente mínima.
_MIN_SAMPLES_FOR_MEDIAN = 3
_MAX_SAMPLES_PER_STAGE = 20

# A42.l22 — o no-op auto-declarado (`output_summary.skipped == true`) sai da
# amostra. Ele grava `completed` de propósito (`_STAGE_STATUS_BY_OUTCOME`,
# ADR-357 §2) e por isso atravessava o filtro de status, misturando execuções de
# milissegundos com execuções de minutos. Não confundir com
# `PipelineStageStatus.skipped`, que é decisão pré-execução do orquestrador e já
# sai pelo filtro de status.
#
# O corte é de POPULAÇÃO, não estatístico: `estimated_duration_ms` só é lido no
# ramo em que o stage executa de verdade — os early-returns `{"skipped": True}`
# de `extract_baseline` e `extract_irpf_full` (os dois únicos emissores)
# antecedem a leitura de `ctx.stage_duration_estimates`. Quando o stage no-opa,
# nenhuma ETA é emitida: essa amostra nunca pertenceu ao evento previsto.
# Consequência: a janela passa a ser "últimas N execuções reais", não "últimas N
# linhas" — no-op não consome vaga.
#
# A flag é projetada em SQL, e não o `output_summary` inteiro, porque a coluna
# carrega o detail completo do stage (~2,7 KB de média, 4 MB por workspace no
# dogfood) e este read roda no setup de todo run.
_DECLARED_SKIP = PipelineStageLog.output_summary["skipped"].as_boolean()


class PipelineStageLogRepository:
    """Single Responsibility: leitura de ``pipeline_stage_logs``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_median_durations_for_workspace(
        self, workspace_id: str, *, limit_per_stage: int = _MAX_SAMPLES_PER_STAGE
    ) -> dict[str, int]:
        """Mediana de ``duration_ms`` sobre as últimas ``limit_per_stage`` execuções reais de cada stage."""
        rows = self._session.execute(
            select(PipelineStageLog.stage, PipelineStageLog.duration_ms, _DECLARED_SKIP)
            .join(PipelineRun, PipelineStageLog.pipeline_run_id == PipelineRun.id)
            .where(
                PipelineRun.workspace_id == workspace_id,
                PipelineStageLog.status == PipelineStageStatus.completed,
                PipelineStageLog.duration_ms.isnot(None),
            )
            .order_by(PipelineStageLog.started_at.desc())
        ).all()
        return _medians_from_rows(rows, limit_per_stage=limit_per_stage)


def _medians_from_rows(
    rows: list[tuple[str, int, bool | None]], *, limit_per_stage: int
) -> dict[str, int]:
    by_stage: dict[str, list[int]] = {}
    for stage, duration_ms, declared_skip in rows:
        if declared_skip:
            continue
        samples = by_stage.setdefault(stage, [])
        if len(samples) < limit_per_stage:
            samples.append(duration_ms)
    return {
        stage: int(statistics.median(samples))
        for stage, samples in by_stage.items()
        if len(samples) >= _MIN_SAMPLES_FOR_MEDIAN
    }
