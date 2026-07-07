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


def _apolice_sintetica() -> dict:
    """Apólice PII-zero (placa/CNPJ sintéticos NÃO podem vazar no resumo)."""
    return {
        "apolice_numero": "AUTO-1",
        "seguradora": "tokiomarine",
        "vigencia_inicio": "2026-03-01",
        "vigencia_fim": "2027-03-01",
        "premio_total_brl": "1500.00",
        "corretor": {"cpf_or_cnpj": "12345678000199"},
        "bens_segurados": [{"tipo": "veiculo", "placa": "ABC1D23", "coberturas": []}],
    }


def _e4_unified_schema() -> dict:
    import json

    path = Path(__file__).resolve().parents[3] / "config" / "schemas" / "e4_unified.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _conta_com_despesa_duplicada() -> dict:
    """Payload E3 com 2 despesas idênticas (colapsam no dedup K4) + 1 receita."""
    mercado = {"data": "2026-01-10", "descricao": "MERCADO", "valor": -100, "tipo": "debito"}
    salario = {"data": "2026-01-05", "descricao": "SALARIO EMP", "valor": 5000, "tipo": "credito"}
    return {
        "banco": "Itaú",
        "tipo_conta": "extratoconta",
        "moeda": "BRL",
        "titular": "david",
        "transacoes": [mercado, dict(mercado), salario],
    }


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

    def test_build_patrimonio_artifact_from_empty_baseline_omits(self):
        """ADR-132 T2: baseline vazio → ``None`` (sinal "omitir chave").

        Antes (legado): retornava ``{"dados": []}``, que sobrescrevia o E4
        patrimônio bom em re-runs sem reprocessar IRPF. Agora omite a chave
        e o fallback workspace-scoped do read() resolve.
        """
        n = type("Fake", (), {"data": {}})()
        assert build_patrimonio_artifact(n) is None

    def test_build_patrimonio_artifact_from_none_baseline_omits(self):
        """ADR-132 T2: baseline ``None`` → ``None``."""
        assert build_patrimonio_artifact(None) is None

    def test_build_patrimonio_artifact_passes_through_data(self):
        n = type("Fake", (), {"data": {"patrimonio_por_ano": {"2024": {}}}})()
        out = build_patrimonio_artifact(n)
        assert out == {"patrimonio_por_ano": {"2024": {}}}


# =============================================================================
# serialize_e4_artifacts
# =============================================================================


class TestSerializeE4Artifacts:
    def test_produces_all_seven_keys_when_baseline_present(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E1.5c",
            "baseline_patrimonial",
            {"data_consolidacao": "2025-06-30", "membros_familia": [{"nome": "David"}]},
        )
        store.seed(
            "E3",
            "a",
            {
                "banco": "Itaú",
                "tipo_conta": "extratoconta",
                "moeda": "BRL",
                "titular": "david",
                "transacoes": [
                    {
                        "data": "2026-01-05",
                        "descricao": "SALARIO EMP",
                        "valor": 5000,
                        "tipo": "credito",
                    },
                    {"data": "2026-01-10", "descricao": "MERCADO", "valor": -100, "tipo": "debito"},
                ],
            },
        )
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        assert set(payloads.keys()) == set(ARTIFACT_KEYS)

    def test_receitas_payload_matches_legacy_shape(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E3",
            "a",
            {
                "banco": "Itaú",
                "tipo_conta": "extratoconta",
                "moeda": "BRL",
                "titular": "david",
                "transacoes": [
                    {
                        "data": "2026-01-05",
                        "descricao": "SALARIO EMP",
                        "valor": 5000,
                        "tipo": "credito",
                    },
                ],
            },
        )
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        r = payloads["receitas"]
        assert r["total_geral"] == 5000.0
        assert r["total_transacoes"] == 1
        assert r["categorias"] == ["receita_clt"]
        assert "consolidation_date" in r

    def test_despesas_payload_has_absolute_values(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E3",
            "a",
            {
                "banco": "Itaú",
                "tipo_conta": "extratoconta",
                "moeda": "BRL",
                "titular": "david",
                "transacoes": [
                    {"data": "2026-01-10", "descricao": "MERCADO", "valor": -100, "tipo": "debito"},
                ],
            },
        )
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        d = payloads["despesas"]
        assert d["total_geral"] == 100.0  # valor absoluto

    def test_despesas_carries_conferencia_lineage_signals(self):
        """A25.l5 (ADR-279 N2): ``despesas`` é o único payload E4 com bloco
        ``_lineage`` — transporte dos sinais de dedup que sobrevive ao modo
        incremental (E5 re-roda sozinho lendo artefatos persistidos)."""
        store = InMemoryArtifactStore()
        store.seed("E3", "a", _conta_com_despesa_duplicada())
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        block = payloads["despesas"]["_lineage"]
        assert block["lineage_version"] == "1.0"
        assert block["signals"] == {
            "tx_total": "3",
            "dedup_collapsed": "1",
            "dedup_review": "0",
        }
        for key in ("receitas", "fluxo_mensal_detalhado", "investimentos", "seguros"):
            assert "_lineage" not in payloads[key]

    def test_patrimonio_omitted_when_no_baseline(self):
        """ADR-132 T2 (defesa em profundidade): sem baseline, ``patrimonio`` é
        **omitido** do payload — em vez de gravar ``{"dados": []}`` e
        sobrescrever o E4 bom de runs anteriores. O caller (``categorize_transactions.
        _e4_persist_artifacts``) só escreve as chaves presentes; o read()
        com fallback workspace-scoped (T1) resolve a ausência.
        """
        store = InMemoryArtifactStore()
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        assert "patrimonio" not in payloads

    def test_patrimonio_uses_normalized_baseline_when_present(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E1.5c",
            "baseline_patrimonial",
            {
                "data_consolidacao": "2025-06-30",
                "membros_familia": [{"nome": "David"}],
            },
        )
        result = _adapter().categorize_via_store(store)

        payloads = serialize_e4_artifacts(result)

        # Baseline normalizado propaga data_processamento, membros, etc.
        assert payloads["patrimonio"]["data_processamento"] == "2025-06-30"
        assert "David" in payloads["patrimonio"]["membros"]

    def test_investimentos_has_totals(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E2-llm",
            "btg",
            {
                "instituicao": "BTG",
                "tipo": "investimentosposicao",
                "membro": "david",
                "data_referencia": "2026-03-31",
                "posicoes": [{"nome": "Tesouro", "valor_total": 100_000}],
            },
        )
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

    def test_seguros_v2_com_apolices_resumidas(self):
        """A28.l6: apólices de ``extract_comprovantes_bens`` populam o balde
        ``seguros`` (contrato v2) com resumos LGPD-safe — sem CPF/placa."""
        result = _adapter().categorize_via_store(InMemoryArtifactStore())

        payloads = serialize_e4_artifacts(result, apolices=[_apolice_sintetica()])

        seguros = payloads["seguros"]
        assert seguros["schema_version"] == "2"
        assert len(seguros["apolices"]) == 1
        assert seguros["apolices"][0]["apolice_numero"] == "AUTO-1"
        assert seguros["apolices"][0]["premio_total_brl"] == "1500.00"
        blob = str(seguros)
        assert "ABC1D23" not in blob
        assert "12345678000199" not in blob

    def test_seguros_v2_valida_contra_schema_e4_unified(self):
        """Branch ``seguros`` explícito no e4_unified.schema.json (A28.l6)."""
        jsonschema = pytest.importorskip("jsonschema")
        result = _adapter().categorize_via_store(InMemoryArtifactStore())

        payloads = serialize_e4_artifacts(result, apolices=[_apolice_sintetica()])

        jsonschema.validate(payloads["seguros"], _e4_unified_schema())
        jsonschema.validate(empty_placeholder(), _e4_unified_schema())


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
