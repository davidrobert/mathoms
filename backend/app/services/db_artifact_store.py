"""DBArtifactStore — implementação SQLAlchemy do protocolo ``ArtifactStore``.

Vive em ``backend/app/services/`` porque depende de SQLAlchemy — a fronteira
arquitetural de ``pipeline/`` proíbe imports de fastapi/celery/sqlalchemy
(ver ``dev/check_pipeline_boundaries.py``).

**Gerenciamento de sessão (ADR-083):** a sessão é injetada pelo chamador
(Celery task ou teste). O store não cria nem fecha sessão própria — o
chamador controla ``commit`` / ``rollback`` / ``close``. Isso garante que toda
a run compartilha uma transação e evita sessões órfãs.

**Sem ``flush`` por-write:** writes/deletes apenas marcam o estado na sessão;
o flush acontece naturalmente no ``commit`` do chamador (fim de stage em
``pipeline_task._record_stage_result``) ou via ``autoflush`` antes de queries
subsequentes na mesma sessão. Flush por-operação produzia contenção de
write-lock em SQLite quando stages gravavam milhares de artefatos em série.

Semântica:
    - ``write`` é upsert por ``(pipeline_run_id, stage, artifact_key)``.
    - ``read`` devolve o artefato do ``pipeline_run_id`` fixado no construtor;
      para leitura cross-run use ``PipelineArtifactRepository``.
    - ``list_keys`` devolve distinct keys no workspace (cross-run) para o stage.
    - ``delete_stage`` remove apenas os artefatos do run atual — runs
      anteriores permanecem intocadas.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models.pipeline_artifact import PipelineArtifact


class DBArtifactStore:
    """Persistência de artefatos em ``pipeline_artifacts`` via SQLAlchemy."""

    def __init__(
        self,
        session: Session,
        *,
        workspace_id: str,
        pipeline_run_id: str,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._pipeline_run_id = pipeline_run_id

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    @property
    def pipeline_run_id(self) -> str:
        return self._pipeline_run_id

    def _get(self, stage: str, key: str) -> Optional[PipelineArtifact]:
        return (
            self._session.query(PipelineArtifact)
            .filter_by(
                pipeline_run_id=self._pipeline_run_id,
                stage=stage,
                artifact_key=key,
            )
            .one_or_none()
        )

    def read(self, stage: str, key: str) -> Optional[dict]:
        row = self._get(stage, key)
        return row.content_json if row else None

    def list_keys(self, stage: str) -> list[str]:
        rows = (
            self._session.query(PipelineArtifact.artifact_key)
            .filter_by(workspace_id=self._workspace_id, stage=stage)
            .distinct()
            .order_by(PipelineArtifact.artifact_key.asc())
            .all()
        )
        return [r[0] for r in rows]

    def exists(self, stage: str, key: str) -> bool:
        return self._get(stage, key) is not None

    def write(
        self,
        stage: str,
        key: str,
        data: dict,
        *,
        document_id: Optional[str] = None,
    ) -> None:
        row = self._get(stage, key)
        if row is None:
            row = PipelineArtifact(
                workspace_id=self._workspace_id,
                pipeline_run_id=self._pipeline_run_id,
                stage=stage,
                artifact_key=key,
                document_id=document_id,
                content_json=data,
            )
            self._session.add(row)
        else:
            row.content_json = data
            if document_id is not None:
                row.document_id = document_id

    def delete(self, stage: str, key: str) -> None:
        row = self._get(stage, key)
        if row is not None:
            self._session.delete(row)

    def delete_stage(self, stage: str) -> int:
        count = (
            self._session.query(PipelineArtifact)
            .filter_by(pipeline_run_id=self._pipeline_run_id, stage=stage)
            .delete(synchronize_session=False)
        )
        return int(count or 0)
