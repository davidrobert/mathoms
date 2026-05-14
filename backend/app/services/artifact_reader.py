"""Reader unificado de artefatos do pipeline (DB-first + fallback disco).

Com ``MATHOMS_USE_DB_ARTIFACTS=True`` (default), stages gravam artefatos só em
``pipeline_artifacts``. Leitores legados em ``backend/app/services/`` que
apontavam para ``tenant_root/processed/<dir>/*.json`` recebiam dados stale
(run anterior) ou vazios.

Este módulo oferece ``read_latest_artifact`` — DB primeiro, disco como
back-compat (CLI dev com ``DiskArtifactStore`` + migração). Fonte do
layout de disco: ``pipeline.artifact_store.stage_dir_name/suffix``.

**ADR-212 PR3b (planejado):** fallback disco será removido junto com a
deleção de ``DiskArtifactStore``. PR3a manteve para não cascatar refactor
em readers como ``compute_progress`` que escrevem fixture em disco. Cada
caller será migrado individualmente em PR3b.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.app.core.database import SyncSessionLocal
from backend.app.repositories.pipeline_artifact_repository import PipelineArtifactRepository
from pipeline.artifact_store import stage_dir_name, stage_suffix
from pipeline.stage_spec import resolve_stage_name, to_legacy_stage_name

logger = logging.getLogger(__name__)


def _stage_query_candidates(stage: str) -> list[str]:
    """Janela compat F9.2 → F9.6 (ADR-093): runners ainda escrevem nomes
    legados ("E4"/"E5"...) mas callers podem chamar com forma descritiva.
    Retorna formas a tentar em ordem (input, descritivo, legado), sem
    duplicatas. Disco só usa o ``stage`` original (já tem alias em
    ``_STAGE_TO_DIR``).
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


def _read_from_disk(tenant_root: Path | str, *, stage: str, key: str) -> dict[str, Any] | None:
    """Fallback: lê ``tenant_root/processed/<dir>/<key><suffix>``."""
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

    DB query tenta ambas as formas (legacy + descritiva) durante a janela
    F9.2 → F9.6 (ADR-093) — primeiro hit vence.
    """
    db_payload = _read_from_db(workspace_id, stage=stage, key=key)
    if db_payload is not None:
        return db_payload
    if tenant_root is None:
        return None
    return _read_from_disk(tenant_root, stage=stage, key=key)
