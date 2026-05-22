"""Tests — ``E4CategorizerAdapter`` (Sessão A4a)."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.services.baseline_normalizer import BaselineNormalizer  # noqa: E402
from pipeline.domain.services.cash_flow_builder import CashFlowBuilder  # noqa: E402
from pipeline.domain.services.e4_categorizer_adapter import (  # noqa: E402
    CategorizationResult,
    E4CategorizerAdapter,
)
from pipeline.domain.services.investments_consolidator import (  # noqa: E402
    InvestmentsConsolidator,
)
from pipeline.domain.services.transaction_classifier import (  # noqa: E402
    ClassifierConfig,
    TransactionClassifier,
)

GOLDENS_DIR = Path(__file__).resolve().parents[2] / "pipeline" / "goldens" / "e4"
_FIXED_NOW = datetime(2026, 4, 19, 10, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
_FIXED_DATE = date(2026, 4, 19)


def _load_golden(name: str) -> dict:
    return json.loads((GOLDENS_DIR / name).read_text(encoding="utf-8"))


def _seed_from_golden(store: InMemoryArtifactStore, golden: dict) -> None:
    for entry in golden.get("e3_accounts", []):
        store.seed("E3", entry["key"], entry["payload"])
    if "baseline" in golden:
        store.seed("E1.5c", "baseline_patrimonial", golden["baseline"])
    for pos in golden.get("e2_positions", []):
        store.seed(pos["stage"], pos["key"], pos["payload"])


def _adapter_from_golden(golden: dict) -> E4CategorizerAdapter:
    """Constrói adapter com configs + clocks fixos para determinismo."""
    classifier_cfg = ClassifierConfig.from_configs(
        categorization=golden.get("categorization"),
        family=golden.get("family"),
    )
    from pipeline.domain.services.investments_consolidator import (
        InvestmentsConsolidatorConfig,
    )

    inv_cfg = InvestmentsConsolidatorConfig.from_family(golden.get("family"))

    return E4CategorizerAdapter(
        classifier=TransactionClassifier(classifier_cfg),
        cash_flow_builder=CashFlowBuilder(now=_FIXED_NOW),
        baseline_normalizer=BaselineNormalizer(date_today=_FIXED_DATE),
        investments_consolidator=InvestmentsConsolidator(inv_cfg, now=_FIXED_NOW),
    )


# =============================================================================
# Unit — loaders
# =============================================================================


class TestLoaders:
    def test_load_reconciled_accounts_skips_without_transacoes(self):
        store = InMemoryArtifactStore()
        store.seed("E3", "a", {"banco": "X", "transacoes": []})
        store.seed("E3", "b", {"banco": "Y", "transacoes": [{"data": "2026-01-01", "valor": 1}]})

        classifier_cfg = ClassifierConfig.from_configs()
        adapter = E4CategorizerAdapter(classifier=TransactionClassifier(classifier_cfg))

        accounts = adapter.load_reconciled_accounts(store)

        assert len(accounts) == 1
        assert accounts[0]["banco"] == "Y"

    def test_load_baseline_returns_none_when_absent(self):
        store = InMemoryArtifactStore()

        classifier_cfg = ClassifierConfig.from_configs()
        adapter = E4CategorizerAdapter(classifier=TransactionClassifier(classifier_cfg))

        assert adapter.load_baseline(store) is None

    def test_load_investment_positions_filters_by_tipo(self):
        store = InMemoryArtifactStore()
        store.seed("E2-llm", "pos", {"tipo": "investimentosposicao", "posicoes": []})
        store.seed("E2-llm", "not_pos", {"tipo": "extratoconta", "transacoes": []})

        classifier_cfg = ClassifierConfig.from_configs()
        adapter = E4CategorizerAdapter(classifier=TransactionClassifier(classifier_cfg))

        positions = adapter.load_investment_positions(store)

        assert len(positions) == 1
        assert positions[0]["tipo"] == "investimentosposicao"
        assert "_source" in positions[0]

    def test_load_investment_positions_accepts_investment_report(self):
        """E2-llm escreve ``tipo_documento=investment_report`` + ``investimentos``
        para PDFs de portfólio (ex.: BTG). O adapter precisa incluí-los."""
        store = InMemoryArtifactStore()
        store.seed(
            "E2-llm",
            "btg_portfolio",
            {
                "tipo_documento": "investment_report",
                "instituicao": "btgpactual",
                "membro": "mariana_teixeira_ferreira",
                "investimentos": [
                    {
                        "tipo": "cdb",
                        "descricao": "CDB BTG",
                        "valor_brl": 29353.39,
                    }
                ],
            },
        )
        classifier_cfg = ClassifierConfig.from_configs()
        adapter = E4CategorizerAdapter(classifier=TransactionClassifier(classifier_cfg))

        positions = adapter.load_investment_positions(store)

        assert len(positions) == 1
        assert positions[0]["tipo_documento"] == "investment_report"

    def test_load_investment_positions_skips_investment_report_without_items(self):
        """``investment_report`` sem lista ``investimentos`` não é posição."""
        store = InMemoryArtifactStore()
        store.seed(
            "E2-llm",
            "empty_report",
            {"tipo_documento": "investment_report", "investimentos": []},
        )
        classifier_cfg = ClassifierConfig.from_configs()
        adapter = E4CategorizerAdapter(classifier=TransactionClassifier(classifier_cfg))

        assert adapter.load_investment_positions(store) == []

    def test_load_investment_positions_accepts_informe_rendimentos(self):
        """ADR-244 — informe de rendimentos (snapshot 31/12) também é posição.

        Regressão real: workspace `Campos`, informe IR Itaú trouxe
        ``tipo_documento="informe_rendimentos"`` + R$ 290k de CDB no campo
        ``investimentos``. O filter anterior aceitava só ``investment_report``
        → posição descartada → card "Investimentos David Robert" zerado.
        """
        store = InMemoryArtifactStore()
        store.seed(
            "E2-llm",
            "itau_cdbdetalhes_2025",
            {
                "tipo_documento": "informe_rendimentos",
                "instituicao": "itau",
                "membro": "david_robert_camargo_ferreira_campos",
                "investimentos": [
                    {
                        "tipo": "cdb",
                        "descricao": "RDB/CDB - Ag 9652 / Conta 0004397-8",
                        "valor_brl": 290000.0,
                    }
                ],
            },
        )
        classifier_cfg = ClassifierConfig.from_configs()
        adapter = E4CategorizerAdapter(classifier=TransactionClassifier(classifier_cfg))

        positions = adapter.load_investment_positions(store)

        assert len(positions) == 1
        assert positions[0]["tipo_documento"] == "informe_rendimentos"
        assert positions[0]["investimentos"][0]["valor_brl"] == 290000.0

    def test_load_investment_positions_skips_informe_rendimentos_without_investimentos(self):
        """Informe sem campo ``investimentos`` não é posição (só rendimentos)."""
        store = InMemoryArtifactStore()
        store.seed(
            "E2-llm",
            "informe_renda_only",
            {
                "tipo_documento": "informe_rendimentos",
                "instituicao": "nubank",
                "investimentos": [],  # vazio — só rendimentos no doc
            },
        )
        classifier_cfg = ClassifierConfig.from_configs()
        adapter = E4CategorizerAdapter(classifier=TransactionClassifier(classifier_cfg))

        assert adapter.load_investment_positions(store) == []

    def test_load_investment_positions_dedups_by_key_across_stages(self):
        """DiskArtifactStore mapeia os 3 stages E2 para o mesmo dir — dedup
        por key evita ler o mesmo artefato múltiplas vezes."""
        store = InMemoryArtifactStore()
        store.seed(
            "E2-llm", "btg", {"tipo": "investimentosposicao", "posicoes": [{"valor_total": 100}]}
        )
        store.seed(
            "E2-extratos",
            "btg",
            {"tipo": "investimentosposicao", "posicoes": [{"valor_total": 999}]},
        )

        classifier_cfg = ClassifierConfig.from_configs()
        adapter = E4CategorizerAdapter(classifier=TransactionClassifier(classifier_cfg))

        positions = adapter.load_investment_positions(store)

        # Dedupado: só 1 entrada (primeira stage a aparecer na ordem INPUT_STAGES).
        assert len(positions) == 1


# =============================================================================
# from_configs factory
# =============================================================================


class TestFromConfigs:
    def test_builds_adapter_with_defaults(self):
        adapter = E4CategorizerAdapter.from_configs()
        assert isinstance(adapter, E4CategorizerAdapter)

    def test_builds_with_configs(self):
        adapter = E4CategorizerAdapter.from_configs(
            categorization={"expense_keywords": {"m": ["mercado"]}},
            family={"banco_membro": {"btg": "david"}},
        )
        assert isinstance(adapter, E4CategorizerAdapter)


# =============================================================================
# Goldens
# =============================================================================


class TestGoldenReceitasDespesasSimples:
    def test_matches_expected_counts_and_totals(self):
        golden = _load_golden("cenario_receitas_despesas_simples.json")
        store = InMemoryArtifactStore()
        _seed_from_golden(store, golden)
        adapter = _adapter_from_golden(golden)

        result = adapter.categorize_via_store(store)

        expected = golden["expected"]
        assert len(result.classified) == expected["classified_count"]
        assert result.cash_flow.receitas.total_transacoes == expected["receitas_count"]
        assert result.cash_flow.despesas.total_transacoes == expected["despesas_count"]
        assert result.cash_flow.transferencias_count == expected["transferencias_count"]
        assert result.cash_flow.receitas.total_geral == expected["receitas_total"]
        assert result.cash_flow.despesas.total_geral == expected["despesas_total"]
        assert list(result.cash_flow.receitas.categorias) == expected["receita_categorias"]
        assert list(result.cash_flow.despesas.categorias) == expected["despesa_categorias"]

        # Origem resolvida via IncomeOriginResolver.
        receita_tx = [t for t in result.classified if t.kind == "receita"][0]
        assert receita_tx.origem == expected["receita_origem_esperada"]


class TestGoldenTransferenciaInterna:
    def test_transfers_excluded_from_receitas_despesas(self):
        golden = _load_golden("cenario_transferencia_interna.json")
        store = InMemoryArtifactStore()
        _seed_from_golden(store, golden)
        adapter = _adapter_from_golden(golden)

        result = adapter.categorize_via_store(store)

        expected = golden["expected"]
        assert len(result.classified) == expected["classified_count"]
        assert result.cash_flow.receitas.total_transacoes == expected["receitas_count"]
        assert result.cash_flow.despesas.total_transacoes == expected["despesas_count"]
        assert result.cash_flow.transferencias_count == expected["transferencias_count"]
        assert result.cash_flow.despesas.total_geral == expected["despesas_total"]
        assert list(result.cash_flow.despesas.categorias) == expected["despesa_categorias"]


class TestGoldenBaselineInvestimentos:
    def test_normalizes_baseline_and_consolidates_investments(self):
        golden = _load_golden("cenario_baseline_investimentos.json")
        store = InMemoryArtifactStore()
        _seed_from_golden(store, golden)
        adapter = _adapter_from_golden(golden)

        result = adapter.categorize_via_store(store)

        expected = golden["expected"]
        assert len(result.classified) == expected["classified_count"]

        # Baseline normalizado.
        assert len(result.baseline.fixes) >= expected["baseline_fixes_min_count"]
        if expected["baseline_has_patrimonio_por_ano"]:
            assert "patrimonio_por_ano" in result.baseline.data
            assert "2024" in result.baseline.data["patrimonio_por_ano"]
        if expected["baseline_has_imoveis_consolidados"]:
            imoveis = result.baseline.data["imoveis_consolidados"]
            assert imoveis[0]["descricao"] == expected["baseline_imovel_descricao"]
            assert imoveis[0]["proprietario"] == expected["baseline_imovel_proprietario"]

        # Investimentos consolidados.
        inv = result.investments
        assert inv.n_posicoes == expected["investments_n_posicoes"]
        assert inv.total_por_membro == expected["investments_total_por_membro"]
        assert inv.total_geral == expected["investments_total_geral"]


# =============================================================================
# Result type + determinism
# =============================================================================


class TestResult:
    def test_categorize_returns_frozen_result(self):
        golden = _load_golden("cenario_receitas_despesas_simples.json")
        store = InMemoryArtifactStore()
        _seed_from_golden(store, golden)
        adapter = _adapter_from_golden(golden)

        result = adapter.categorize_via_store(store)

        assert isinstance(result, CategorizationResult)
        assert result.accounts_loaded == 2

    def test_empty_store_produces_empty_result(self):
        store = InMemoryArtifactStore()
        adapter = E4CategorizerAdapter.from_configs()

        result = adapter.categorize_via_store(store)

        assert result.accounts_loaded == 0
        assert len(result.classified) == 0
        assert result.cash_flow.receitas.total_geral == 0.0
        assert result.cash_flow.despesas.total_geral == 0.0
        assert result.investments.n_posicoes == 0


# =============================================================================
# Schema conformance
# =============================================================================


class TestSchemaConformance:
    def test_receitas_to_legacy_dict_has_required_fields(self):
        """Output tem os campos que o schema ``e4_unified.schema.json``
        (``receitas``) espera."""
        golden = _load_golden("cenario_receitas_despesas_simples.json")
        store = InMemoryArtifactStore()
        _seed_from_golden(store, golden)
        adapter = _adapter_from_golden(golden)

        result = adapter.categorize_via_store(store)
        d = result.cash_flow.receitas.to_legacy_dict()

        for field in (
            "consolidation_date",
            "periodo",
            "categorias",
            "total_categorias",
            "total_transacoes",
            "totais_por_categoria",
            "total_geral",
            "dados",
        ):
            assert field in d

    def test_fluxo_to_legacy_dict_has_receitas_and_despesas_sections(self):
        golden = _load_golden("cenario_receitas_despesas_simples.json")
        store = InMemoryArtifactStore()
        _seed_from_golden(store, golden)
        adapter = _adapter_from_golden(golden)

        result = adapter.categorize_via_store(store)
        d = result.cash_flow.fluxo_mensal.to_legacy_dict()

        assert "receitas" in d
        assert "despesas" in d
        assert "origens" in d["receitas"]
        assert "categorias" in d["despesas"]
        assert "meses_ordenados" in d
