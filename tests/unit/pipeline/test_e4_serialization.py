"""Tests — ``e4_serialization`` (Sessão A4b)."""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.services.baseline_normalizer import BaselineNormalizer  # noqa: E402
from pipeline.domain.services.cash_flow_builder import CashFlowBuilder  # noqa: E402
from pipeline.domain.services.e4_categorizer_adapter import (  # noqa: E402
    E4CategorizerAdapter,
)
from pipeline.domain.services.e4_serialization import (  # noqa: E402
    ARTIFACT_KEYS,
    all_filenames,
    build_patrimonio_artifact,
    empty_placeholder,
    filename_for,
    payloads_to_files,
    serialize_e4_artifacts,
)
from pipeline.domain.services.investments_consolidator import (  # noqa: E402
    InvestmentsConsolidator,
)
from pipeline.domain.services.transaction_classifier import (  # noqa: E402
    ClassifierConfig,
    TransactionClassifier,
)


_FIXED_NOW = datetime(2026, 4, 19, 10, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
_FIXED_DATE = date(2026, 4, 19)


def _adapter() -> E4CategorizerAdapter:
    cfg = ClassifierConfig.from_configs(
        categorization={
            "expense_keywords": {"mercado": ["mercado"]},
            "income_keywords": {"receita_clt": ["salario"]},
            "internal_transfer_patterns": [],
            "clt_source_mapping": {"emp": "Empregador X"},
            "pj_source_mapping": {},
        },
    )
    return E4CategorizerAdapter(
        classifier=TransactionClassifier(cfg),
        cash_flow_builder=CashFlowBuilder(now=_FIXED_NOW),
        baseline_normalizer=BaselineNormalizer(date_today=_FIXED_DATE),
        investments_consolidator=InvestmentsConsolidator(now=_FIXED_NOW),
    )


# =============================================================================
# ARTIFACT_KEYS / filenames
# =============================================================================


class TestArtifactKeys:
    def test_all_seven_keys_are_defined(self):
        assert len(ARTIFACT_KEYS) == 7
        assert set(ARTIFACT_KEYS) == {
            "receitas",
            "despesas",
            "fluxo_mensal_detalhado",
            "patrimonio",
            "investimentos",
            "seguros",
            "pontos_milhas",
        }

    def test_filename_for_maps_to_legacy_suffix(self):
        assert filename_for("receitas") == "receitas-4_unified.json"
        assert filename_for("seguros") == "seguros-4_unified.json"

    def test_filename_for_invalid_raises(self):
        with pytest.raises(KeyError):
            filename_for("unknown")

    def test_all_filenames_preserves_canonical_order(self):
        names = all_filenames()
        assert names[0] == "receitas-4_unified.json"
        assert names[-1] == "pontos_milhas-4_unified.json"
        assert len(names) == 7


# =============================================================================
# Placeholders
# =============================================================================


class TestPlaceholders:
    def test_empty_placeholder_has_dados_empty_list(self):
        p = empty_placeholder()
        assert p == {"dados": []}

    def test_build_patrimonio_artifact_from_empty_baseline(self):
        n = type("Fake", (), {"data": {}})()
        assert build_patrimonio_artifact(n) == {"dados": []}

    def test_build_patrimonio_artifact_from_none_baseline(self):
        assert build_patrimonio_artifact(None) == {"dados": []}

    def test_build_patrimonio_artifact_passes_through_data(self):
        n = type("Fake", (), {"data": {"patrimonio_por_ano": {"2024": {}}}})()
        out = build_patrimonio_artifact(n)
        assert out == {"patrimonio_por_ano": {"2024": {}}}


# =============================================================================
# serialize_e4_artifacts
# =============================================================================


class TestSerializeE4Artifacts:
    def test_produces_all_seven_keys(self):
        store = InMemoryArtifactStore()
        store.seed("E3", "a", {
            "banco": "Itaú", "tipo_conta": "extratoconta",
            "moeda": "BRL", "titular": "david",
            "transacoes": [
                {"data": "2026-01-05", "descricao": "SALARIO EMP", "valor": 5000, "tipo": "credito"},
                {"data": "2026-01-10", "descricao": "MERCADO", "valor": -100, "tipo": "debito"},
            ],
        })
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        assert set(payloads.keys()) == set(ARTIFACT_KEYS)

    def test_receitas_payload_matches_legacy_shape(self):
        store = InMemoryArtifactStore()
        store.seed("E3", "a", {
            "banco": "Itaú", "tipo_conta": "extratoconta",
            "moeda": "BRL", "titular": "david",
            "transacoes": [
                {"data": "2026-01-05", "descricao": "SALARIO EMP", "valor": 5000, "tipo": "credito"},
            ],
        })
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        r = payloads["receitas"]
        assert r["total_geral"] == 5000.0
        assert r["total_transacoes"] == 1
        assert r["categorias"] == ["receita_clt"]
        assert "consolidation_date" in r

    def test_despesas_payload_has_absolute_values(self):
        store = InMemoryArtifactStore()
        store.seed("E3", "a", {
            "banco": "Itaú", "tipo_conta": "extratoconta",
            "moeda": "BRL", "titular": "david",
            "transacoes": [
                {"data": "2026-01-10", "descricao": "MERCADO", "valor": -100, "tipo": "debito"},
            ],
        })
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        d = payloads["despesas"]
        assert d["total_geral"] == 100.0  # valor absoluto

    def test_patrimonio_empty_when_no_baseline(self):
        store = InMemoryArtifactStore()
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        assert payloads["patrimonio"] == {"dados": []}

    def test_patrimonio_uses_normalized_baseline_when_present(self):
        store = InMemoryArtifactStore()
        store.seed("E1.5c", "baseline_patrimonial", {
            "data_consolidacao": "2025-06-30",
            "membros_familia": [{"nome": "David"}],
        })
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        # Baseline normalizado propaga data_processamento, membros, etc.
        assert payloads["patrimonio"]["data_processamento"] == "2025-06-30"
        assert "David" in payloads["patrimonio"]["membros"]

    def test_investimentos_has_totals(self):
        store = InMemoryArtifactStore()
        store.seed("E2-llm", "btg", {
            "instituicao": "BTG", "tipo": "investimentosposicao",
            "membro": "david", "data_referencia": "2026-03-31",
            "posicoes": [{"nome": "Tesouro", "valor_total": 100_000}],
        })
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        assert payloads["investimentos"]["total_geral"] == 100_000.0
        assert payloads["investimentos"]["n_posicoes"] == 1

    def test_seguros_and_pontos_milhas_are_empty_placeholders(self):
        store = InMemoryArtifactStore()
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        assert payloads["seguros"] == {"dados": []}
        assert payloads["pontos_milhas"] == {"dados": []}


# =============================================================================
# payloads_to_files
# =============================================================================


class TestPayloadsToFiles:
    def test_converts_keys_to_filenames(self):
        payloads = {
            "receitas": {"total_geral": 100},
            "seguros": {"dados": []},
        }

        mapped = payloads_to_files(payloads)

        assert "receitas-4_unified.json" in mapped
        assert "seguros-4_unified.json" in mapped
        assert mapped["receitas-4_unified.json"]["total_geral"] == 100
