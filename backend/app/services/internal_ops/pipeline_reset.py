"""Reset workspace pipeline artifacts a partir de stage (ADR-212 PR1b).

Substitui `scripts/e_reset.py --from <stage>` (deletado neste PR). Operação
DB-only: deleta rows em `pipeline_artifacts` com `(workspace_id, stage)` no
cascade derivado de `FULL_ORDER` em `pipeline/stage_spec.py`.

Out-of-scope vs `e_reset.py` legado (ADR-212 §Não-objetivos):
- `--move-to-inbox`: operação disco; não aplica no caminho DB-only.
- `validate` / `strip_narrativas` / `run_script`: workflows dev-CLI sem
  contrapartida no console interno.
- UX interativa / wall info: específico de CLI.

Consumidor: console interno (ADR-116, IA-0 local-only); endpoint HTTP
pós-IA-1.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.workspace import Workspace
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult
from backend.app.services.storage.artifact_references import referenced_artifact_ids_async
from pipeline.stage_spec import (
    FULL_ORDER,
    resolve_stage_name,
    to_legacy_stage_name,
)

__all__ = ["reset_workspace_from_stage"]


def _cascade_stage_names(canonical_stage: str) -> list[str]:
    """Stages a serem deletadas: `canonical_stage` + tudo depois em `FULL_ORDER`.

    Inclui legacy names porque DB pode ter rows pré-F9.3 (ADR-093 janela
    de compat). Set evita duplicatas quando descritivo == legacy.
    """
    from_idx = FULL_ORDER.index(canonical_stage)
    descriptive = FULL_ORDER[from_idx:]
    legacy = [to_legacy_stage_name(s) for s in descriptive]
    return sorted(set(descriptive) | set(legacy))


async def _artifact_ids(db: AsyncSession, workspace_id: str, stages: list[str]) -> list[int]:
    stmt = (
        select(PipelineArtifact.id)
        .where(PipelineArtifact.workspace_id == workspace_id)
        .where(PipelineArtifact.stage.in_(stages))
    )
    return list((await db.execute(stmt)).scalars().all())


async def _split_by_reference(
    db: AsyncSession, workspace_id: str, stages: list[str]
) -> tuple[list[int], int]:
    """`(deletáveis, preservados)`. Artefato referenciado por report / publicação
    / parecer nunca entra no delete (ADR-371): `RESTRICT` abortaria o batch
    inteiro e `SET NULL`/`CASCADE` destruiria o relatório antigo em silêncio."""
    ids = await _artifact_ids(db, workspace_id, stages)
    referenced = await referenced_artifact_ids_async(db)
    deletable = [i for i in ids if i not in referenced]
    return deletable, len(ids) - len(deletable)


async def _execute_delete(db: AsyncSession, deletable_ids: list[int]) -> int:
    if not deletable_ids:
        return 0
    result = await db.execute(
        delete(PipelineArtifact).where(PipelineArtifact.id.in_(deletable_ids))
    )
    await db.flush()
    return result.rowcount or 0


def _audit_reset(
    db: AsyncSession,
    actor: str,
    workspace_id: str,
    canonical_stage: str,
    stages_affected: list[str],
    deleted: int,
    preserved: int,
) -> None:
    details = {
        "from_stage": canonical_stage,
        "stages_affected": stages_affected,
        "artifacts_deleted": deleted,
        "artifacts_preserved_referenced": preserved,
    }
    record = AuditRecord(
        "pipeline.reset_from_stage", actor, "workspace", workspace_id, details=details
    )
    append_audit(record, db)


async def reset_workspace_from_stage(
    db: AsyncSession,
    *,
    workspace_id: str,
    from_stage: str,
    actor: str,
    preview: bool = True,
) -> OpResult:
    """Reseta artefatos de pipeline do workspace a partir de stage.

    `from_stage` aceita nome descritivo (`"reconcile_transactions"`) ou
    legacy (`E3`) — resolvido via `resolve_stage_name`. Cascade inclui
    `from_stage` em si + todos os stages subsequentes em `FULL_ORDER`.

    Args:
        db: sessão async; caller controla `commit()`/`rollback()`.
        workspace_id: UUID do workspace.
        from_stage: stage canónica ou legacy.
        actor: identificador do operador (audit log).
        preview: True (default) retorna counts sem mutar DB; False executa
            DELETE e registra entry de audit.

    Returns:
        `OpResult.success` com detalhes ou `OpResult.failure(error)`.
        Erros: `workspace_not_found`, `unknown_stage`.
    """
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        return OpResult.failure("workspace_not_found", workspace_id=workspace_id)

    canonical_stage = resolve_stage_name(from_stage)
    if canonical_stage not in FULL_ORDER:
        return OpResult.failure(
            "unknown_stage",
            from_stage=from_stage,
            valid_stages=FULL_ORDER,
        )

    stages_to_match = _cascade_stage_names(canonical_stage)
    deletable, preserved = await _split_by_reference(db, workspace_id, stages_to_match)
    artifacts_affected = len(deletable)
    stages_descriptive = FULL_ORDER[FULL_ORDER.index(canonical_stage) :]

    if preview:
        return OpResult.success(
            preview=True,
            workspace_id=workspace_id,
            from_stage=canonical_stage,
            stages_affected=stages_descriptive,
            artifacts_affected=artifacts_affected,
            artifacts_preserved_referenced=preserved,
        )

    deleted = await _execute_delete(db, deletable)
    _audit_reset(db, actor, workspace_id, canonical_stage, stages_descriptive, deleted, preserved)
    return OpResult.success(
        preview=False,
        workspace_id=workspace_id,
        from_stage=canonical_stage,
        stages_affected=stages_descriptive,
        artifacts_affected=artifacts_affected,
        artifacts_deleted=deleted,
        artifacts_preserved_referenced=preserved,
    )
