"""Disposição de um stage: o que a não-entrega significa para o run (ADR-357 §2)."""

# Módulo puro e framework-free de propósito — `pipeline/**` não importa
# `fastapi`/`celery`/`sqlalchemy` (`dev/check_pipeline_boundaries.py`), e a
# tradução `StageOutcome → PipelineStageStatus` (que toca o enum SQLAlchemy) mora
# em `backend/app/tasks/pipeline_task.py`.
#
# A disposição combina **retorno do stage** com **criticidade do registry**. Quem
# produz o valor não decide o próprio raio de explosão: o contrato
# `{"degraded": True}` foi rejeitado justamente por dar essa caneta ao produtor
# (ADR-357 §2 · Alternativas rejeitadas).

from __future__ import annotations

from enum import Enum

from pipeline.stage_spec import STAGE_REGISTRY, resolve_stage_name

REQUIRED = "required"
DEGRADABLE = "degradable"

VALID_CRITICALITIES: frozenset[str] = frozenset({REQUIRED, DEGRADABLE})


class StageOutcome(str, Enum):
    """Desfecho de uma execução de stage — `degraded` não entregou e não veta o entregável."""

    completed = "completed"
    skipped = "skipped"
    degraded = "degraded"
    failed = "failed"

    @property
    def delivered(self) -> bool:
        return self in (StageOutcome.completed, StageOutcome.skipped)


def stage_criticality(stage: str) -> str:
    """Criticidade declarada no registry; `required` para stage desconhecido (fail-closed)."""
    # Stage fora do registry (ex.: o `"No runner found"` do orquestrador) nunca
    # ganha licença de degradar por omissão.
    spec = STAGE_REGISTRY.get(resolve_stage_name(stage))
    if spec is None:
        return REQUIRED
    return spec.criticality


def commits_artifacts_on_degrade(stage: str) -> bool:
    """Se o stage commita artefatos coletados ao degradar em vez de rollback (ADR-357 §6)."""
    spec = STAGE_REGISTRY.get(resolve_stage_name(stage))
    if spec is None:
        return False
    return spec.commit_artifacts_on_degrade


def resolve_stage_outcome(
    stage: str,
    *,
    delivered: bool,
    declared_skip: bool = False,
) -> StageOutcome:
    """Combina `(retorno, criticality)` no desfecho do stage (ADR-357 §2)."""
    # `delivered=False` cobre **as duas** rotas de não-entrega — `success: False`
    # e exceção que esgotou os retries — porque a disposição é cega à FORMA da
    # não-entrega. `result.error` não entra na assinatura de propósito:
    # `error is None` significa "nenhuma exceção cruzou a fronteira do runner",
    # não "o stage declarou", e a mesma falha de rede cai dos dois lados
    # conforme a linha em que estoura.
    if delivered:
        return StageOutcome.skipped if declared_skip else StageOutcome.completed
    if stage_criticality(stage) == DEGRADABLE:
        return StageOutcome.degraded
    return StageOutcome.failed
