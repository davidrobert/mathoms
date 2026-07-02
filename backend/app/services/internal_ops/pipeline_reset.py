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


async def _count_artifacts(db: AsyncSession, workspace_id: str, stages: list[str]) -> int:
    stmt = (
        select(PipelineArtifact.id)
        .where(PipelineArtifact.workspace_id == workspace_id)
        .where(PipelineArtifact.stage.in_(stages))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return len(rows)


async def _execute_delete(db: AsyncSession, workspace_id: str, stages: list[str]) -> int:
    stmt = (
        delete(PipelineArtifact)
        .where(PipelineArtifact.workspace_id == workspace_id)
        .where(PipelineArtifact.stage.in_(stages))
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount or 0


def _audit_reset(
    actor: str,
    workspace_id: str,
    canonical_stage: str,
    stages_affected: list[str],
    deleted: int,
) -> None:
    append_audit(
        AuditRecord(
            action="pipeline.reset_from_stage",
            actor=actor,
            target_type="workspace",
            target_id=workspace_id,
            details={
                "from_stage": canonical_stage,
                "stages_affected": stages_affected,
                "artifacts_deleted": deleted,
            },
        )
    )


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
    artifacts_affected = await _count_artifacts(db, workspace_id, stages_to_match)
    stages_descriptive = FULL_ORDER[FULL_ORDER.index(canonical_stage) :]

    if preview:
        return OpResult.success(
            preview=True,
            workspace_id=workspace_id,
            from_stage=canonical_stage,
            stages_affected=stages_descriptive,
            artifacts_affected=artifacts_affected,
        )

    deleted = await _execute_delete(db, workspace_id, stages_to_match)
    _audit_reset(actor, workspace_id, canonical_stage, stages_descriptive, deleted)
    return OpResult.success(
        preview=False,
        workspace_id=workspace_id,
        from_stage=canonical_stage,
        stages_affected=stages_descriptive,
        artifacts_affected=artifacts_affected,
        artifacts_deleted=deleted,
    )
