"""Unit tests — ``pipeline.artifact_store`` protocols e implementação in-memory.

Cobre Fase 1 (Foundation) do plano de migração:

- ``InMemoryArtifactStore`` passa todos os checks do protocolo.
- ``InMemoryArtifactStore.seed()`` fluent builder funciona; estado não vaza
  entre testes (pytest cria instância nova por teste).
- ``ReadableArtifactStore`` e ``ArtifactStore`` são reconhecidos via
  ``isinstance`` (``@runtime_checkable``).
- ``_STAGE_TO_DIR`` e ``_STAGE_TO_SUFFIX`` têm a mesma cobertura de stages
  (mapeamentos permanecem para referência de layout legado em disco).

**ADR-212 PR3b:** ``DiskArtifactStore`` foi removido. Testes de disk store
ficaram obsoletos e foram deletados — ``DBArtifactStore`` (em produção) é
testado em ``backend/tests/test_db_artifact_store.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import (  # noqa: E402
    _STAGE_TO_SUFFIX,
    ArtifactStore,
    InMemoryArtifactStore,
    ReadableArtifactStore,
    stage_suffix,
)
from pipeline.stage_spec import STAGE_RENAME_MAP  # noqa: E402

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
# Mapeamento de stage → sufixo
# (`_STAGE_TO_DIR` deletado em ADR-213 — dead code sem caller runtime)
# =============================================================================


class TestStageMappings:
    def test_resolver_works_for_known_stages(self):
        for stage in _STAGE_TO_SUFFIX:
            assert stage_suffix(stage) == _STAGE_TO_SUFFIX[stage]

    def test_resolver_raises_for_unknown_stage(self):
        with pytest.raises(KeyError):
            stage_suffix("not-a-stage")

    def test_e1_members_mapping(self):
        """E1 registrado (ADR-127)."""
        assert _STAGE_TO_SUFFIX["E1"] == "-1b_unified.json"

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
            assert stage in _STAGE_TO_SUFFIX, f"{stage} faltando em _STAGE_TO_SUFFIX"

    def test_legacy_descriptive_parity(self):
        """Paridade legacy ↔ descritivo em ``_STAGE_TO_SUFFIX`` (ADR-093 · W2-T06).

        Janela de compat F9.2 → F9.6: todo par ``(legacy, descritivo)`` de
        ``STAGE_RENAME_MAP`` que produz artifact deve ter o **mesmo sufixo**
        em ambas as keys. Garante que ``stage_suffix(descritivo)`` não levante
        ``KeyError`` quando o adapter migrar do nome legado.

        Exceções documentadas:
          - ``E0-unlock`` / ``E0-route``: ``writes=()`` — sem artifact por design.
          - ``E1.6``: legacy nunca exposto (ADR-157 nasceu descritivo); só o
            descritivo ``extract_irpf_full`` está em ``_STAGE_TO_SUFFIX``.
        """
        skip_legacy = {"E0-unlock", "E0-route", "E1.6"}
        for legacy, descriptive in STAGE_RENAME_MAP.items():
            if legacy in skip_legacy:
                continue
            assert (
                legacy in _STAGE_TO_SUFFIX
            ), f"legacy '{legacy}' (→ '{descriptive}') ausente em _STAGE_TO_SUFFIX"
            assert (
                descriptive in _STAGE_TO_SUFFIX
            ), f"descritivo '{descriptive}' (← '{legacy}') ausente em _STAGE_TO_SUFFIX"
            assert _STAGE_TO_SUFFIX[legacy] == _STAGE_TO_SUFFIX[descriptive], (
                f"sufixo divergente: {legacy}={_STAGE_TO_SUFFIX[legacy]!r} "
                f"vs {descriptive}={_STAGE_TO_SUFFIX[descriptive]!r}"
            )

    def test_dead_code_suffixes_preserved(self):
        """``E5.N`` (-5n_narrativas) e ``E7`` (-7_crossval) são dead code de
        write em produção (CLAUDE.md §"Convenções de naming"), mas devem
        permanecer no mapping para consumers de leitura/rastreabilidade.
        """
        assert _STAGE_TO_SUFFIX["E5.N"] == "-5n_narrativas.json"
        assert _STAGE_TO_SUFFIX["generate_narratives"] == "-5n_narrativas.json"
        assert _STAGE_TO_SUFFIX["E7"] == "-7_crossval.json"
        assert _STAGE_TO_SUFFIX["E7-crossval"] == "-7_crossval.json"
        assert _STAGE_TO_SUFFIX["validate_cross"] == "-7_crossval.json"
