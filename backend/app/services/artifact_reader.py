"""Reader DB-only de artefatos do pipeline (ADR-212 PR3b).

Stages gravam artefatos em ``pipeline_artifacts`` via ``DBArtifactStore``.
Este módulo oferece ``read_latest_artifact`` para readers em
``backend/app/services/`` que precisam consultar artefatos de runs
recentes.

Fallback de disco foi removido em ADR-212 PR3b — caminho
``DiskArtifactStore`` não existe mais em produção. O parâmetro
``tenant_root`` permanece na assinatura por compatibilidade com callers
legados (``transaction_service``, ``dashboard_service``); emite warning
de deprecation quando passado não-None.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.app.core.database import SyncSessionLocal
from backend.app.repositories.pipeline_artifact_repository import PipelineArtifactRepository
from pipeline.stage_spec import resolve_stage_name, to_legacy_stage_name

logger = logging.getLogger(__name__)


def _stage_query_candidates(stage: str) -> list[str]:
    """Janela compat F9.2 → F9.6 (ADR-093): runners ainda escrevem nomes
    legados ("E4"/"E5"...) mas callers podem chamar com forma descritiva.
    Retorna formas a tentar em ordem (input, descritivo, legado), sem
    duplicatas.
    """
    descriptive = resolve_stage_name(stage)
    legacy = to_legacy_stage_name(descriptive)
    seen: list[str] = [stage]
    for alt in (descriptive, legacy):
        if alt not in seen:
            seen.append(alt)
    return seen


def _read_from_db(workspace_id: str, *, stage: str, key: str) -> dict[str, Any] | None:
    """DB query tentando ambas as formas (legacy + descritiva)."""
    with SyncSessionLocal() as db:
        repo = PipelineArtifactRepository(db)
        for candidate in _stage_query_candidates(stage):
            art = repo.get_latest_for_workspace(workspace_id, stage=candidate, artifact_key=key)
            if art is not None and art.content_json is not None:
                return art.content_json
    return None


def read_latest_artifact(
    workspace_id: str,
    *,
    stage: str,
    key: str,
    tenant_root: Path | str | None = None,
) -> dict[str, Any] | None:
    """Retorna o payload do artefato mais recente para (workspace, stage, key).

    Consulta apenas ``pipeline_artifacts`` (ADR-212 PR3b — fallback disco
    removido). DB query tenta nomes legacy + descritivo durante a janela
    F9.2 → F9.6 (ADR-093). Retorna ``None`` se não existe.

    ``tenant_root`` permanece na assinatura por compatibilidade com callers
    legados; é ignorado e emite warning de deprecation quando passado
    não-None.
    """
    if tenant_root is not None:
        logger.warning(
            "read_latest_artifact: tenant_root deprecated (ADR-212 PR3b). "
            "Caller=%s/%s — remover argumento; fallback disco morreu.",
            stage,
            key,
        )
    return _read_from_db(workspace_id, stage=stage, key=key)
