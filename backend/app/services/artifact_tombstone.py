"""Tombstone de artifacts E2* na reclassificação de documento (ADR-311 D1).

Artifacts E2 nunca eram invalidados: ``_find_unprocessed_docs`` pula
qualquer key existente, então reclassificar um documento deixava para trás
o artifact do contrato antigo envenenando o E3 a cada run (dogfood
2026-07-07, órfãos purgados pela A32.l1). Este módulo mata a classe na
raiz: mudou ``doc_type``/``bank_code`` → deleta os artifacts E2* daquele
documento, restrito por ``workspace_id + documento + stage``.

Vive no backend adapter — ``pipeline/`` não importa SQLAlchemy
(``dev/check_pipeline_boundaries.py``). Padrão de invalidação destrutiva
controlada: ``internal_ops/pipeline_reset.py``.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_artifact import PipelineArtifact
from pipeline.artifact_store import stage_aliases

_logger = logging.getLogger("mathoms.pipeline.artifact")

# Stages de extração per-documento (família E2*). Rows antigas podem estar
# na grafia legada — expandido via stage_aliases (ADR-093), nunca literal
# único. "E2" plano cobre rows pré-F9.2 sem sufixo.
_E2_DESCRIPTIVE_STAGES: tuple[str, ...] = (
    "extract_statements",
    "extract_invoices",
    "extract_with_llm",
    "extract_informe_aluguel",
    "extract_informes_anuais",
    "extract_comprovantes_bens",
)

_HASH_PREFIX_LEN = 12


def e2_tombstone_stage_names() -> tuple[str, ...]:
    """Todas as grafias (legacy + descritiva) dos stages E2* alvo do tombstone."""
    names: set[str] = {"E2"}
    for stage in _E2_DESCRIPTIVE_STAGES:
        names.update(stage_aliases(stage))
    return tuple(sorted(names))


def _document_match_conditions(document_id: str, content_hash: str | None) -> list:
    """FK ``document_id`` quando populada + prefixo ``content_hash[:12]_`` da key (ADR-084) — writers E2 históricos gravam a FK como NULL; ``autoescape`` impede o ``_`` de virar wildcard do LIKE."""
    conditions = [PipelineArtifact.document_id == document_id]
    prefix = (content_hash or "")[:_HASH_PREFIX_LEN]
    if len(prefix) == _HASH_PREFIX_LEN:
        conditions.append(PipelineArtifact.artifact_key.startswith(f"{prefix}_", autoescape=True))
    return conditions


def _log_tombstone(workspace_id: str, document_id: str, deleted: int) -> None:
    _logger.info(
        "mathoms.pipeline.artifact.tombstone_reclassify",
        extra={
            "workspace_id": workspace_id,
            "document_id": document_id,
            "artifacts_deleted": deleted,
        },
    )


async def tombstone_e2_artifacts_for_document(
    db: AsyncSession,
    *,
    workspace_id: str,
    document_id: str,
    content_hash: str | None,
) -> int:
    """Deleta os artifacts E2* de um documento reclassificado. Retorna a contagem."""
    stmt = (
        delete(PipelineArtifact)
        .where(PipelineArtifact.workspace_id == workspace_id)
        .where(PipelineArtifact.stage.in_(e2_tombstone_stage_names()))
        .where(or_(*_document_match_conditions(document_id, content_hash)))
    )
    result = await db.execute(stmt)
    deleted = int(result.rowcount or 0)
    if deleted:
        _log_tombstone(workspace_id, document_id, deleted)
    return deleted
