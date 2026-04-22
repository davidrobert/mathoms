"""Tests — ``pipeline.stage_spec`` (Fase 1.5.1).

Cobre:
- ``STAGE_REGISTRY`` completo (todos os stages legados).
- ``FULL_ORDER`` validado contra dependências.
- ``build_from_map`` produz o mesmo ``FROM_MAP`` do orquestrador antigo.
- ``validate_full_order`` falha quando dependência vem depois do consumidor.
- ``validate_artifact_stage`` aceita executável + virtual, rejeita desconhecido.
- ``STAGE_RENAME_MAP`` é exaustivo e bijetivo (guardrail Fase 9).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.stage_spec import (  # noqa: E402
    DETERMINISTIC_ORDER,
    FULL_ORDER,
    LEGACY_FROM_ALIASES,
    STAGE_REGISTRY,
    STAGE_RENAME_MAP,
    VIRTUAL_ARTIFACT_STAGES,
    build_from_map,
    validate_artifact_stage,
    validate_full_order,
)

EXPECTED_LEGACY_STAGES = {
    "E0-audit",
    "E0-unlock",
    "E0-route",
    "E1",
    "E1.5",
    "E1.5c",
    "E2-faturas",
    "E2-extratos",
    "E2-llm",
    "E3",
    "E4",
    "E5",
    "E5.N",
    "E6",
    "E7-crossval",
    "E7-review",
    "E7-apply",
    "E6-final",
}


class TestRegistry:
    def test_registry_covers_all_legacy_stages(self):
        assert set(STAGE_REGISTRY.keys()) == EXPECTED_LEGACY_STAGES

    def test_full_order_matches_registry(self):
        assert set(FULL_ORDER) == set(STAGE_REGISTRY.keys())

    def test_deterministic_order_has_no_llm_stages(self):
        for s in DETERMINISTIC_ORDER:
            assert not STAGE_REGISTRY[s].is_llm

    def test_deterministic_order_preserves_full_order_sequence(self):
        positions = [FULL_ORDER.index(s) for s in DETERMINISTIC_ORDER]
        assert positions == sorted(positions)


class TestBuildFromMap:
    def test_includes_stage_itself(self):
        m = build_from_map(["a", "b", "c"])
        assert m == {"a": ["a", "b", "c"], "b": ["b", "c"], "c": ["c"]}

    def test_on_full_order(self):
        m = build_from_map(FULL_ORDER)
        # Sanidade: "a partir de E3" inclui E3 até E6-final
        assert m["E3"][0] == "E3"
        assert m["E3"][-1] == "E6-final"
        # Todos os E5.* aparecem após E5
        e5_idx = m["E5"]
        assert e5_idx[0] == "E5"
        assert "E5.N" in e5_idx


class TestValidateFullOrder:
    def test_registered_order_is_consistent(self):
        validate_full_order(FULL_ORDER)  # no raise

    def test_unknown_stage_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_full_order(FULL_ORDER + ["not-a-stage"])

    def test_dependency_after_consumer_raises(self):
        # Invariante: E5 precisa de E4; invertendo a ordem → AssertionError
        bad = [s for s in FULL_ORDER]
        i4 = bad.index("E4")
        i5 = bad.index("E5")
        bad[i4], bad[i5] = bad[i5], bad[i4]
        with pytest.raises(AssertionError):
            validate_full_order(bad)

    def test_virtual_stage_is_respected(self):
        # E6-final lê E5-revised (virtual). A ordem canônica deve passar.
        validate_full_order(FULL_ORDER)
        # Remover E7-apply (produtor de E5-revised) deve fazer falhar.
        bad = [s for s in FULL_ORDER if s != "E7-apply"]
        with pytest.raises(AssertionError):
            validate_full_order(bad)


class TestValidateArtifactStage:
    def test_accepts_executable_stage(self):
        for stage in STAGE_REGISTRY:
            validate_artifact_stage(stage)  # no raise

    def test_accepts_virtual_stage(self):
        for stage in VIRTUAL_ARTIFACT_STAGES:
            validate_artifact_stage(stage)

    def test_rejects_unknown(self):
        with pytest.raises(ValueError):
            validate_artifact_stage("not-a-stage")


class TestStageRenameMap:
    def test_covers_all_legacy_names(self):
        """STAGE_RENAME_MAP inclui todo key do REGISTRY + virtual stages."""
        expected_keys = set(STAGE_REGISTRY.keys()) | set(VIRTUAL_ARTIFACT_STAGES)
        assert set(STAGE_RENAME_MAP.keys()) == expected_keys

    def test_is_bijective(self):
        values = list(STAGE_RENAME_MAP.values())
        assert len(values) == len(set(values)), "Colisão no STAGE_RENAME_MAP"

    def test_new_names_are_snake_case_descriptive(self):
        """Sanity check: novos nomes seguem convenção (snake_case em inglês)."""
        for new in STAGE_RENAME_MAP.values():
            assert new.islower() or "_" in new
            assert "-" not in new  # nenhum hífen — apenas underscore
            assert " " not in new


class TestLegacyAliases:
    def test_aliases_point_to_real_stages(self):
        for alias, target in LEGACY_FROM_ALIASES.items():
            assert target in STAGE_REGISTRY
