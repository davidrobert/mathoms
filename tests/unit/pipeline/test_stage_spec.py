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
    DESCRIPTIVE_TO_LEGACY,
    DETERMINISTIC_ORDER,
    FULL_ORDER,
    LEGACY_FROM_ALIASES,
    LEGACY_TO_DESCRIPTIVE,
    STAGE_REGISTRY,
    STAGE_RENAME_MAP,
    VIRTUAL_ARTIFACT_STAGES,
    build_from_map,
    resolve_stage_name,
    to_legacy_stage_name,
    validate_artifact_stage,
    validate_full_order,
)

EXPECTED_DESCRIPTIVE_STAGES = {
    "audit_documents",
    "unlock_documents",
    "route_documents",
    "extract_members",
    "extract_baseline",
    "consolidate_baseline",
    "extract_irpf_full",
    "extract_invoices",
    "extract_statements",
    "extract_with_llm",
    "reconcile_transactions",
    "categorize_transactions",
    "analyze_finances",
    "generate_narratives",
    "validate_cross",
    "review_finances_holistic",
}


class TestRegistry:
    def test_registry_covers_all_descriptive_stages(self):
        assert set(STAGE_REGISTRY.keys()) == EXPECTED_DESCRIPTIVE_STAGES

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
        # Sanidade: "a partir de reconcile_transactions" inclui até o último stage
        assert m["reconcile_transactions"][0] == "reconcile_transactions"
        assert m["reconcile_transactions"][-1] == FULL_ORDER[-1]
        # generate_narratives aparece após analyze_finances
        af_idx = m["analyze_finances"]
        assert af_idx[0] == "analyze_finances"
        assert "generate_narratives" in af_idx


class TestValidateFullOrder:
    def test_registered_order_is_consistent(self):
        validate_full_order(FULL_ORDER)  # no raise

    def test_unknown_stage_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_full_order(FULL_ORDER + ["not-a-stage"])

    def test_dependency_after_consumer_raises(self):
        # Invariante: analyze_finances precisa de categorize_transactions;
        # invertendo a ordem → AssertionError
        bad = [s for s in FULL_ORDER]
        i_cat = bad.index("categorize_transactions")
        i_an = bad.index("analyze_finances")
        bad[i_cat], bad[i_an] = bad[i_an], bad[i_cat]
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
    def test_values_cover_registry_plus_virtual(self):
        """STAGE_RENAME_MAP values incluem todo key do REGISTRY + virtual stages."""
        expected_descriptive = set(STAGE_REGISTRY.keys()) | set(VIRTUAL_ARTIFACT_STAGES)
        assert set(STAGE_RENAME_MAP.values()) == expected_descriptive

    def test_is_bijective(self):
        values = list(STAGE_RENAME_MAP.values())
        assert len(values) == len(set(values)), "Colisão no STAGE_RENAME_MAP"

    def test_new_names_are_snake_case_descriptive(self):
        """Sanity check: novos nomes seguem convenção (snake_case em inglês)."""
        for new in STAGE_RENAME_MAP.values():
            assert new.islower() or "_" in new
            assert "-" not in new  # nenhum hífen — apenas underscore
            assert " " not in new

    def test_legacy_to_descriptive_alias(self):
        assert LEGACY_TO_DESCRIPTIVE is STAGE_RENAME_MAP

    def test_descriptive_to_legacy_inverse(self):
        for legacy, descriptive in STAGE_RENAME_MAP.items():
            assert DESCRIPTIVE_TO_LEGACY[descriptive] == legacy


class TestResolveStageName:
    def test_legacy_returns_descriptive(self):
        assert resolve_stage_name("E3") == "reconcile_transactions"
        assert resolve_stage_name("E5.N") == "generate_narratives"
        assert resolve_stage_name("E7-crossval") == "validate_cross"

    def test_descriptive_passthrough(self):
        assert resolve_stage_name("reconcile_transactions") == "reconcile_transactions"
        assert resolve_stage_name("analyze_finances") == "analyze_finances"

    def test_unknown_passthrough(self):
        assert resolve_stage_name("unknown_stage") == "unknown_stage"

    def test_to_legacy_inverse(self):
        assert to_legacy_stage_name("reconcile_transactions") == "E3"
        assert to_legacy_stage_name("E3") == "E3"  # passthrough


class TestLegacyAliases:
    def test_aliases_point_to_real_stages(self):
        for alias, target in LEGACY_FROM_ALIASES.items():
            assert target in STAGE_REGISTRY
