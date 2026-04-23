"""DB → disco materialization para leitores legados (E6).

Regressão: quando DBArtifactStore escreve artefatos só no DB, E6 render_report
lê disco stale e produz HTML com dados antigos (ex.: patrimônio sem imóveis
pós-cutover para MATHOMS_USE_DB_ARTIFACTS=True).
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.artifact_store import DiskArtifactStore, InMemoryArtifactStore
from pipeline.stage_materialization import materialize_stages_to_root


def test_materialize_writes_db_artifacts_to_disk(tmp_path: Path) -> None:
    store = InMemoryArtifactStore()
    store.seed("E5", "analise_financeira", {"patrimonio": {"bruto": 4_308_452.40}})
    store.seed("E4", "patrimonio", {"dados": [{"tipo": "imovel", "valor_brl": 1_000_000}]})

    written = materialize_stages_to_root(store, tmp_path, ["E5", "E4"])

    assert written == 2
    e5_path = tmp_path / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    e4_path = tmp_path / "processed" / "E4_unified" / "patrimonio-4_unified.json"
    assert json.loads(e5_path.read_text())["patrimonio"]["bruto"] == 4_308_452.40
    assert json.loads(e4_path.read_text())["dados"][0]["tipo"] == "imovel"


def test_materialize_noop_for_disk_store(tmp_path: Path) -> None:
    """Com DiskArtifactStore, disco já é a fonte de verdade — não duplicar."""
    store = DiskArtifactStore(tmp_path)
    store.write("E5", "analise_financeira", {"x": 1})
    # Limpar disco para provar que materialize_stages_to_root NÃO re-escreve
    (tmp_path / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json").unlink()

    written = materialize_stages_to_root(store, tmp_path, ["E5"])

    assert written == 0
    assert not (
        tmp_path / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    ).exists()


def test_materialize_virtual_stage_uses_e5_layout(tmp_path: Path) -> None:
    """E5-revised é virtual — vai para E5_analysis/*-5_analysis.json."""
    store = InMemoryArtifactStore()
    store.seed("E5-revised", "analise_financeira", {"revised": True})

    written = materialize_stages_to_root(store, tmp_path, ["E5-revised"])

    assert written == 1
    path = tmp_path / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    assert json.loads(path.read_text()) == {"revised": True}


def test_materialize_empty_stage_skips(tmp_path: Path) -> None:
    store = InMemoryArtifactStore()
    written = materialize_stages_to_root(store, tmp_path, ["E5", "E4"])
    assert written == 0
