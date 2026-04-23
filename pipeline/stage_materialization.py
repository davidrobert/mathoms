"""Materialização DB → disco para leitores legados (E6 render).

Durante MATHOMS_USE_DB_ARTIFACTS=True (ADR-083), stages como E5/E4/E1.5c
escrevem só em `pipeline_artifacts`. Mas `scripts.e6_render.render_report`
ainda lê JSONs de `ctx.root/processed/<dir>/`. Se o disco está stale (ou
vazio), o relatório HTML mostra dados de runs antigas — ou não mostra
nada (ex.: patrimônio sem imóveis).

Este helper espelha, para o root real, os artefatos que o store tem em DB
— garantindo que E6 leia estado fresco. Não mexe em tmp_dir
(MaterializationBridge faz isso para scripts legados); grava direto em
``<tenant_root>/processed/<dir>/<key><suffix>``.

Fase 9 remove este módulo: E6 migra para ler via ArtifactStore.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pipeline.artifact_store import ArtifactStore, DiskArtifactStore, stage_dir_name, stage_suffix
from pipeline.stage_spec import VIRTUAL_ARTIFACT_STAGES


def _resolve_disk_layout(stage: str) -> tuple[str, str]:
    """Stages virtuais (E5-revised) usam o layout do stage real de origem (E5)."""
    if stage in VIRTUAL_ARTIFACT_STAGES:
        return stage_dir_name("E5"), stage_suffix("E5")
    return stage_dir_name(stage), stage_suffix(stage)


def materialize_stages_to_root(
    store: ArtifactStore,
    tenant_root: Path,
    stages: Iterable[str],
) -> int:
    """Escreve artefatos dos stages informados para ``<tenant_root>/processed/<dir>/``.

    No-op quando ``store`` já é ``DiskArtifactStore`` (disco == fonte de verdade).
    Retorna o número de arquivos gravados.
    """
    if isinstance(store, DiskArtifactStore):
        return 0

    written = 0
    for stage in stages:
        dir_name, suffix = _resolve_disk_layout(stage)
        target_dir = tenant_root / "processed" / dir_name
        target_dir.mkdir(parents=True, exist_ok=True)
        for key in store.list_keys(stage):
            data = store.read(stage, key)
            if data is None:
                continue
            path = target_dir / f"{key}{suffix}"
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            written += 1
    return written
