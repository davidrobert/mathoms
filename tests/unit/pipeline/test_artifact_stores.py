"""Unit tests — ``pipeline.artifact_store`` protocols e implementações.

Cobre Fase 1 (Foundation) do plano de migração:

- ``DiskArtifactStore`` produz mesmo resultado que I/O direto em disco.
- ``InMemoryArtifactStore`` passa todos os checks do protocolo.
- ``InMemoryArtifactStore.seed()`` fluent builder funciona; estado não vaza
  entre testes (pytest cria instância nova por teste).
- ``ReadableArtifactStore`` e ``ArtifactStore`` são reconhecidos via
  ``isinstance`` (``@runtime_checkable``).
- ``_STAGE_TO_DIR`` e ``_STAGE_TO_SUFFIX`` têm a mesma cobertura de stages.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import (  # noqa: E402
    _STAGE_TO_DIR,
    _STAGE_TO_SUFFIX,
    ArtifactStore,
    DiskArtifactStore,
    InMemoryArtifactStore,
    ReadableArtifactStore,
    stage_dir_name,
    stage_suffix,
)

# =============================================================================
# InMemoryArtifactStore
# =============================================================================


class TestInMemoryArtifactStore:
    def test_write_then_read_round_trip(self):
        store = InMemoryArtifactStore()
        store.write("E2", "itau_202601", {"transactions": [{"v": 1}]})
        assert store.read("E2", "itau_202601") == {"transactions": [{"v": 1}]}

    def test_read_missing_returns_none(self):
        store = InMemoryArtifactStore()
        assert store.read("E2", "nope") is None

    def test_exists(self):
        store = InMemoryArtifactStore()
        assert not store.exists("E2", "x")
        store.write("E2", "x", {"a": 1})
        assert store.exists("E2", "x")

    def test_list_keys_scoped_by_stage_and_sorted(self):
        store = InMemoryArtifactStore()
        store.write("E2", "b", {})
        store.write("E2", "a", {})
        store.write("E3", "z", {})
        assert store.list_keys("E2") == ["a", "b"]
        assert store.list_keys("E3") == ["z"]
        assert store.list_keys("E5") == []

    def test_delete(self):
        store = InMemoryArtifactStore()
        store.write("E2", "x", {"a": 1})
        store.delete("E2", "x")
        assert not store.exists("E2", "x")
        # idempotente
        store.delete("E2", "x")

    def test_delete_stage(self):
        store = InMemoryArtifactStore()
        store.write("E3", "a", {})
        store.write("E3", "b", {})
        store.write("E4", "c", {})
        removed = store.delete_stage("E3")
        assert removed == 2
        assert store.list_keys("E3") == []
        assert store.list_keys("E4") == ["c"]

    def test_seed_is_fluent(self):
        store = (
            InMemoryArtifactStore()
            .seed("E2", "a", {"v": 1})
            .seed("E2", "b", {"v": 2})
            .seed("E3", "c", {"v": 3})
        )
        assert store.read("E2", "a") == {"v": 1}
        assert store.read("E2", "b") == {"v": 2}
        assert store.read("E3", "c") == {"v": 3}

    def test_write_preserves_document_id(self):
        store = InMemoryArtifactStore()
        store.write("E2", "a", {"x": 1}, document_id="doc-42")
        assert store.document_id_for("E2", "a") == "doc-42"

    def test_state_isolated_between_instances(self):
        # Critério de aceite: estado não vaza entre testes.
        store1 = InMemoryArtifactStore()
        store1.write("E2", "a", {"v": 1})
        store2 = InMemoryArtifactStore()
        assert store2.read("E2", "a") is None

    def test_satisfies_artifact_store_protocol(self):
        store = InMemoryArtifactStore()
        assert isinstance(store, ArtifactStore)
        assert isinstance(store, ReadableArtifactStore)


# =============================================================================
# DiskArtifactStore
# =============================================================================


class TestDiskArtifactStore:
    def test_write_then_read_round_trip(self, tmp_path: Path):
        store = DiskArtifactStore(tmp_path)
        data = {"transactions": [{"v": 1}]}
        store.write("E2", "itau_202601", data)
        assert store.read("E2", "itau_202601") == data

    def test_write_creates_expected_disk_layout(self, tmp_path: Path):
        """Sanity check: mesmo layout do legado em ``processed/E2_extracts``."""
        store = DiskArtifactStore(tmp_path)
        store.write("E2", "itau_202601", {"a": 1})
        path = tmp_path / "processed" / "E2_extracts" / "itau_202601-2_extract.json"
        assert path.exists()
        with open(path) as f:
            assert json.load(f) == {"a": 1}

    def test_direct_write_matches_disk_write(self, tmp_path: Path):
        """``DiskArtifactStore.read`` produz o mesmo dict que I/O direto."""
        store = DiskArtifactStore(tmp_path)
        data = {"x": [1, 2, 3], "y": {"z": "v"}}
        # Escrita direta em disco com mesmo layout
        target_dir = tmp_path / "processed" / "E3_reconciled"
        target_dir.mkdir(parents=True)
        (target_dir / "foo-3_reconciled.json").write_text(json.dumps(data))
        assert store.read("E3", "foo") == data

    def test_read_missing_returns_none(self, tmp_path: Path):
        store = DiskArtifactStore(tmp_path)
        assert store.read("E2", "missing") is None

    def test_read_invalid_json_returns_none(self, tmp_path: Path):
        store = DiskArtifactStore(tmp_path)
        target = tmp_path / "processed" / "E2_extracts"
        target.mkdir(parents=True)
        (target / "bad-2_extract.json").write_text("not json {")
        assert store.read("E2", "bad") is None

    def test_list_keys_strips_suffix_and_sorts(self, tmp_path: Path):
        store = DiskArtifactStore(tmp_path)
        store.write("E2", "b", {})
        store.write("E2", "a", {})
        keys = store.list_keys("E2")
        assert keys == ["a", "b"]

    def test_list_keys_ignores_foreign_files(self, tmp_path: Path):
        store = DiskArtifactStore(tmp_path)
        store.write("E2", "good", {})
        # Arquivo que não termina com o sufixo canônico
        foreign = tmp_path / "processed" / "E2_extracts" / "foreign.txt"
        foreign.write_text("x")
        assert store.list_keys("E2") == ["good"]

    def test_exists(self, tmp_path: Path):
        store = DiskArtifactStore(tmp_path)
        assert not store.exists("E2", "x")
        store.write("E2", "x", {})
        assert store.exists("E2", "x")

    def test_delete(self, tmp_path: Path):
        store = DiskArtifactStore(tmp_path)
        store.write("E2", "x", {})
        store.delete("E2", "x")
        assert not store.exists("E2", "x")
        # idempotente
        store.delete("E2", "x")

    def test_delete_stage(self, tmp_path: Path):
        store = DiskArtifactStore(tmp_path)
        store.write("E3", "a", {})
        store.write("E3", "b", {})
        store.write("E4", "c", {})
        removed = store.delete_stage("E3")
        assert removed == 2
        assert store.list_keys("E3") == []
        assert store.list_keys("E4") == ["c"]

    def test_write_is_atomic(self, tmp_path: Path):
        """``write`` usa ``tmp`` + ``replace`` — sem arquivo parcial."""
        store = DiskArtifactStore(tmp_path)
        store.write("E2", "a", {"v": 1})
        # Nenhum .tmp remanescente
        stage_dir = tmp_path / "processed" / "E2_extracts"
        assert list(stage_dir.glob("*.tmp")) == []

    def test_satisfies_artifact_store_protocol(self, tmp_path: Path):
        store = DiskArtifactStore(tmp_path)
        assert isinstance(store, ArtifactStore)
        assert isinstance(store, ReadableArtifactStore)


# =============================================================================
# Mapeamentos de stage
# =============================================================================


class TestStageMappings:
    def test_mappings_have_same_keys(self):
        """``_STAGE_TO_DIR`` e ``_STAGE_TO_SUFFIX`` cobrem os mesmos stages.

        Invariante de segurança: se um stage tem diretório mapeado, deve ter
        sufixo mapeado e vice-versa.
        """
        assert set(_STAGE_TO_DIR.keys()) == set(_STAGE_TO_SUFFIX.keys())

    def test_resolvers_work_for_known_stages(self):
        for stage in _STAGE_TO_DIR:
            assert stage_dir_name(stage) == _STAGE_TO_DIR[stage]
            assert stage_suffix(stage) == _STAGE_TO_SUFFIX[stage]

    def test_resolvers_raise_for_unknown_stage(self):
        with pytest.raises(KeyError):
            stage_dir_name("not-a-stage")
        with pytest.raises(KeyError):
            stage_suffix("not-a-stage")

    def test_e1_members_mapping(self):
        """E1 registrado em ambos os mapeamentos (ADR-127)."""
        assert _STAGE_TO_DIR["E1"] == "members"
        assert _STAGE_TO_SUFFIX["E1"] == "-1b_unified.json"

    def test_e1_round_trip_disk(self, tmp_path: Path):
        store = DiskArtifactStore(tmp_path)
        payload = {"membros": {"david": {"nome_completo": "David"}}, "titular": "david"}
        store.write("E1", "members", payload)
        path = tmp_path / "processed" / "members" / "members-1b_unified.json"
        assert path.exists()
        assert store.read("E1", "members") == payload

    def test_e1_round_trip_in_memory(self):
        store = InMemoryArtifactStore()
        payload = {"membros": {"david": {}}}
        store.write("E1", "members", payload)
        assert store.read("E1", "members") == payload
        assert store.list_keys("E1") == ["members"]

    def test_legacy_e2_variants_all_present(self):
        """E2, E2-faturas, E2-extratos, E2-llm — todos precisam estar mapeados
        porque esses stages existem separadamente em ``STAGE_REGISTRY``.
        """
        for stage in ("E2", "E2-faturas", "E2-extratos", "E2-llm"):
            assert stage in _STAGE_TO_DIR, f"{stage} faltando em _STAGE_TO_DIR"
            assert stage in _STAGE_TO_SUFFIX, f"{stage} faltando em _STAGE_TO_SUFFIX"
