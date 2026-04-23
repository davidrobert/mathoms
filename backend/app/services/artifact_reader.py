"""Reader unificado de artefatos do pipeline (DB-first + fallback disco).

Com ``MATHOMS_USE_DB_ARTIFACTS=True`` (default), stages gravam artefatos só em
``pipeline_artifacts``. Leitores legados em ``backend/app/services/`` que
apontavam para ``tenant_root/processed/<dir>/*.json`` recebiam dados stale
(run anterior) ou vazios.

Este módulo oferece ``read_latest_artifact`` — DB primeiro, disco como
back-compat (CLI dev com ``DiskArtifactStore`` + migração). Fonte do
layout de disco: ``pipeline.artifact_store.stage_dir_name/suffix``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pipeline.artifact_store import stage_dir_name, stage_suffix

from backend.app.core.database import SyncSessionLocal
from backend.app.repositories.pipeline_artifact_repository import PipelineArtifactRepository

logger = logging.getLogger(__name__)


def read_latest_artifact(
    workspace_id: str,
    *,
    stage: str,
    key: str,
    tenant_root: Path | str | None = None,
) -> dict[str, Any] | None:
    """Retorna o payload do artefato mais recente para (workspace, stage, key).

    Ordem: DB (``pipeline_artifacts``) → disco (``tenant_root/processed/<dir>/<key><suffix>``).
    ``None`` quando não existe em nenhum dos dois.
    """
    with SyncSessionLocal() as db:
        repo = PipelineArtifactRepository(db)
        art = repo.get_latest_for_workspace(workspace_id, stage=stage, artifact_key=key)
        if art is not None and art.content_json is not None:
            return art.content_json

    if tenant_root is None:
        return None
    try:
        dir_name = stage_dir_name(stage)
        suffix = stage_suffix(stage)
    except KeyError:
        return None
    path = Path(tenant_root) / "processed" / dir_name / f"{key}{suffix}"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Falha ao ler artefato de disco %s: %s", path, exc)
        return None
