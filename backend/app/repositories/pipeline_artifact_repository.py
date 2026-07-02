"""PipelineArtifactRepository — queries de leitura/limpeza em ``pipeline_artifacts``.

Encapsula queries comuns para que `DBArtifactStore` não precise construir SQL
ad-hoc e para expor operações cross-run (o store é escopado a um ``pipeline_run_id``).

Uso:

    repo = PipelineArtifactRepository(session)
    latest = repo.get_latest_for_workspace(workspace_id, stage="analyze_finances")
    by_doc = repo.get_by_document(document_id, stage="E2")
    repo.delete_stage_for_run(run_id, stage="reconcile_transactions")
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.models.pipeline_artifact import PipelineArtifact
from pipeline.artifact_store import stage_aliases


class PipelineArtifactRepository:
    """Single Responsibility: leitura e limpeza de ``pipeline_artifacts``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_latest_for_workspace(
        self, workspace_id: str, *, stage: str, artifact_key: Optional[str] = None
    ) -> Optional[PipelineArtifact]:
        """Artefato mais recente para ``(workspace, stage[, key])`` — ``created_at``
        desc com tie-break por ``id`` autoincrement: dois writes no mesmo flush
        empatam ``created_at`` no microssegundo e o resultado vira arbitrário."""
        q = (
            select(PipelineArtifact)
            .where(
                PipelineArtifact.workspace_id == workspace_id,
                # legado ↔ descritivo (ADR-093, janela F9)
                PipelineArtifact.stage.in_(stage_aliases(stage)),
            )
            .order_by(PipelineArtifact.created_at.desc(), PipelineArtifact.id.desc())
        )
        if artifact_key is not None:
            q = q.where(PipelineArtifact.artifact_key == artifact_key)
        return self._session.execute(q.limit(1)).scalar_one_or_none()

    def list_latest_keys(self, workspace_id: str, *, stage: str) -> list[str]:
        """Lista distinct ``artifact_key`` para o workspace+stage (ordenada)."""
        rows = self._session.execute(
            select(PipelineArtifact.artifact_key)
            .where(
                PipelineArtifact.workspace_id == workspace_id,
                PipelineArtifact.stage.in_(stage_aliases(stage)),
            )
            .distinct()
            .order_by(PipelineArtifact.artifact_key.asc())
        ).all()
        return [r[0] for r in rows]

    def get_by_document(
        self, document_id: str, *, stage: Optional[str] = None
    ) -> list[PipelineArtifact]:
        """Todos os artefatos ligados a um documento (E2-* tipicamente)."""
        q = select(PipelineArtifact).where(PipelineArtifact.document_id == document_id)
        if stage is not None:
            q = q.where(PipelineArtifact.stage.in_(stage_aliases(stage)))
        return list(self._session.execute(q).scalars().all())

    def delete_stage_for_run(self, pipeline_run_id: str, *, stage: str) -> int:
        """Remove artefatos do stage na run. Retorna contagem removida."""
        stmt = delete(PipelineArtifact).where(
            PipelineArtifact.pipeline_run_id == pipeline_run_id,
            PipelineArtifact.stage.in_(stage_aliases(stage)),
        )
        result = self._session.execute(stmt)
        self._session.flush()
        return int(result.rowcount or 0)

    def delete_stages_for_run(self, pipeline_run_id: str, *, stages: list[str]) -> int:
        """Remove artefatos dos stages informados. Retorna total removido."""
        if not stages:
            return 0
        expanded = sorted({a for s in stages for a in stage_aliases(s)})
        stmt = delete(PipelineArtifact).where(
            PipelineArtifact.pipeline_run_id == pipeline_run_id,
            PipelineArtifact.stage.in_(expanded),
        )
        result = self._session.execute(stmt)
        self._session.flush()
        return int(result.rowcount or 0)

    def delete_all_for_workspace(self, workspace_id: str) -> int:
        """Remove todos os artefatos de um workspace — usado em reset total."""
        stmt = delete(PipelineArtifact).where(PipelineArtifact.workspace_id == workspace_id)
        result = self._session.execute(stmt)
        self._session.flush()
        return int(result.rowcount or 0)
