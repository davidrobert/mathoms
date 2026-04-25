"""Tests — ``pipeline.materialization_bridge`` (Fase 2.2)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.materialization_bridge import MaterializationBridge  # noqa: E402
from pipeline.stage_spec import STAGE_REGISTRY  # noqa: E402


class TestContextManager:
    def test_tmp_dir_created_on_enter(self, tmp_path):
        store = InMemoryArtifactStore()
        with MaterializationBridge(store, pipeline_run_id="run1", tmp_root=tmp_path) as b:
            assert b.tmp_dir.exists()
            assert "fin_pipeline_run1" in str(b.tmp_dir)

    def test_tmp_dir_removed_on_exit(self, tmp_path):
        store = InMemoryArtifactStore()
        with MaterializationBridge(store, pipeline_run_id="r", tmp_root=tmp_path) as b:
            td = b.tmp_dir
            (td / "a.txt").write_text("x")
            assert td.exists()
        assert not td.exists()

    def test_tmp_dir_removed_even_on_exception(self, tmp_path):
        store = InMemoryArtifactStore()
        td_captured: Path | None = None
        with pytest.raises(RuntimeError, match="boom"):
            with MaterializationBridge(store, pipeline_run_id="r", tmp_root=tmp_path) as b:
                td_captured = b.tmp_dir
                (td_captured / "a.txt").write_text("x")
                raise RuntimeError("boom")
        assert td_captured is not None
        assert not td_captured.exists()

    def test_tmp_dir_access_outside_with_raises(self, tmp_path):
        store = InMemoryArtifactStore()
        bridge = MaterializationBridge(store, pipeline_run_id="r", tmp_root=tmp_path)
        with pytest.raises(RuntimeError, match="fora de"):
            _ = bridge.tmp_dir


class TestHydrateForStage:
    def test_reads_from_store_and_writes_disk(self, tmp_path):
        store = InMemoryArtifactStore()
        store.seed("E2-extratos", "itau_202601", {"transactions": [{"v": 1}]})
        store.seed("E2-faturas", "nubank_202601", {"transactions": [{"v": 2}]})
        with MaterializationBridge(store, pipeline_run_id="r", tmp_root=tmp_path) as b:
            root = b.hydrate_for_stage("E3")
            assert root == b.tmp_dir
            expected_dir = b.processed_dir() / "E2_extracts"
            assert expected_dir.exists()
            itau_file = expected_dir / "itau_202601-2_extract.json"
            nubank_file = expected_dir / "nubank_202601-2_extract.json"
            assert itau_file.exists()
            assert nubank_file.exists()
            assert json.loads(itau_file.read_text()) == {"transactions": [{"v": 1}]}

    def test_unknown_stage_raises(self, tmp_path):
        store = InMemoryArtifactStore()
        with MaterializationBridge(store, pipeline_run_id="r", tmp_root=tmp_path) as b:
            with pytest.raises(KeyError):
                b.hydrate_for_stage("not-a-stage")


class TestPersistFromStage:
    def test_writes_from_disk_to_store(self, tmp_path):
        store = InMemoryArtifactStore()
        with MaterializationBridge(store, pipeline_run_id="r", tmp_root=tmp_path) as b:
            # Simular saída do script E3: escrever arquivos no dir esperado
            e3_dir = b.processed_dir() / "E3_reconciled"
            e3_dir.mkdir(parents=True)
            (e3_dir / "itau_BRL-3_reconciled.json").write_text('{"net": 100}')
            (e3_dir / "nubank_BRL-3_reconciled.json").write_text('{"net": -50}')
            count = b.persist_from_stage("E3")
            assert count == 2
            assert store.read("E3", "itau_BRL") == {"net": 100}
            assert store.read("E3", "nubank_BRL") == {"net": -50}


class TestMappingsComplete:
    """Guardrail: stages que armazenam JSON em ``processed/`` têm entry nos
    mapas ``_STAGE_TO_DIR``/``_STAGE_TO_SUFFIX``.

    Stages excluídos do bridge (escreveram/leram em outros lugares):
    - ``E0-*``: não produzem pipeline_artifacts.
    - ``E1``/``E1.5``: saídas em ``members/`` (não ``processed/``).
    """

    # Stages que NÃO são mediados pelo bridge (JSON em ``processed/``).
    _NON_BRIDGE_STAGES = frozenset({"E0-audit", "E0-unlock", "E0-route", "E1", "E1.5"})

    def test_bridge_covered_stages_all_mapped(self):
        from pipeline.artifact_store import _STAGE_TO_DIR, _STAGE_TO_SUFFIX
        from pipeline.stage_spec import VIRTUAL_ARTIFACT_STAGES

        all_referenced: set[str] = set()
        for spec in STAGE_REGISTRY.values():
            for s in spec.reads:
                all_referenced.add(s)
            for s in spec.writes:
                all_referenced.add(s)
        # Virtuais usam o layout do E5; não-bridge stages por design ficam fora.
        all_referenced -= VIRTUAL_ARTIFACT_STAGES
        all_referenced -= self._NON_BRIDGE_STAGES
        missing_dir = all_referenced - set(_STAGE_TO_DIR)
        missing_suffix = all_referenced - set(_STAGE_TO_SUFFIX)
        assert not missing_dir, f"Faltam entradas em _STAGE_TO_DIR: {missing_dir}"
        assert not missing_suffix, f"Faltam entradas em _STAGE_TO_SUFFIX: {missing_suffix}"
