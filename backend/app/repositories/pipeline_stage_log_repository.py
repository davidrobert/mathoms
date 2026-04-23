"""PipelineStageLogRepository — queries de leitura de ``pipeline_stage_logs``.

Uso primário (ADR-119): mediana de duração por stage para estimativa de
tempo honesta na UI. Query é agregada por-stage e filtra apenas runs
bem-sucedidos (status=completed).
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


class PipelineStageLogRepository:
    """Single Responsibility: leitura de ``pipeline_stage_logs``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_median_durations_for_workspace(
        self, workspace_id: str, *, limit_per_stage: int = _MAX_SAMPLES_PER_STAGE
    ) -> dict[str, int]:
        """Mediana de ``duration_ms`` por stage no workspace.

        Janela: últimos ``limit_per_stage`` runs de cada stage, só onde
        ``status == completed`` e ``duration_ms IS NOT NULL``. Stages com
        <3 amostras são omitidos (ruído estatístico).
        """
        rows = self._session.execute(
            select(PipelineStageLog.stage, PipelineStageLog.duration_ms)
            .join(PipelineRun, PipelineStageLog.pipeline_run_id == PipelineRun.id)
            .where(
                PipelineRun.workspace_id == workspace_id,
                PipelineStageLog.status == PipelineStageStatus.completed,
                PipelineStageLog.duration_ms.isnot(None),
            )
            .order_by(PipelineStageLog.started_at.desc())
        ).all()
        return _medians_from_rows(rows, limit_per_stage=limit_per_stage)


def _medians_from_rows(rows: list[tuple[str, int]], *, limit_per_stage: int) -> dict[str, int]:
    by_stage: dict[str, list[int]] = {}
    for stage, duration_ms in rows:
        samples = by_stage.setdefault(stage, [])
        if len(samples) < limit_per_stage:
            samples.append(duration_ms)
    return {
        stage: int(statistics.median(samples))
        for stage, samples in by_stage.items()
        if len(samples) >= _MIN_SAMPLES_FOR_MEDIAN
    }
