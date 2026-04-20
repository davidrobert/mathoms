"""Tests — ``E5AnalyzerAdapter`` (Sessão A5c)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.services.e5_analyzer_adapter import (  # noqa: E402
    E5AnalysisResult,
    E5AnalyzerAdapter,
)


_DAVID_DOB = date(1985, 6, 15)


def _seed_minimal(store: InMemoryArtifactStore) -> None:
    store.seed("E4", "receitas", {
        "total_geral": 120_000,
        "totais_por_categoria": {"receita_clt": 120_000},
        "dados": {"receita_clt": [{"data": "2026-01-05", "descricao": "SALARIO", "valor": 10_000}]},
        "periodo": "2026-01 a 2026-12",
    })
    store.seed("E4", "despesas", {
        "total_geral": 60_000,
        "totais_por_categoria": {"mercado": 40_000, "uber": 20_000},
        "dados": {
            "mercado": [{"data": "2026-01-10", "descricao": "MERCADO", "valor": 5000}],
            "uber": [{"data": "2026-01-15", "descricao": "UBER", "valor": 3000}],
        },
    })
    store.seed("E4", "fluxo_mensal_detalhado", {
        "meses_ordenados": [f"2026-{m:02d}" for m in range(1, 13)],
        "receitas": {"por_mes": {f"2026-{m:02d}": {"Empregador A": 10_000, "_total": 10_000} for m in range(1, 13)}},
        "despesas": {"por_mes": {f"2026-{m:02d}": {"mercado": 3_333, "uber": 1_667, "_total": 5_000} for m in range(1, 13)}},
    })
    store.seed("E4", "patrimonio", {
        "pipeline_stage": "E1.5",
        "patrimonio_por_ano": {"2024": {"total_bens": 1_500_000, "total_dividas": 200_000}},
        "membros": ["David", "Mariana"],
        "imoveis_consolidados": [
            {"descricao": "Casa Vila Madalena", "valores_31_12": {"2024": 800_000}},
        ],
    })
    store.seed("E4", "investimentos", {
        "total_geral": 500_000,
        "n_posicoes": 3,
        "total_por_membro": {"david": 300_000, "mariana": 200_000},
        "dados": [],
    })


class TestAdapterConstruction:
    def test_from_configs_with_titular_dob_enables_if_projector(self):
        adapter = E5AnalyzerAdapter.from_configs(
            goals={"independencia_financeira": {"if_meta": 5_000_000, "trs_pct": 4.0}},
            titular_dob=_DAVID_DOB,
        )
        # IFProjector deve estar habilitado.
        assert adapter._if_projector is not None

    def test_from_configs_without_titular_dob_disables_if_and_cenarios(self):
        adapter = E5AnalyzerAdapter.from_configs()
        assert adapter._if_projector is None
        assert adapter._cenarios is None

    def test_from_configs_without_goals_keeps_if_disabled(self):
        adapter = E5AnalyzerAdapter.from_configs(titular_dob=_DAVID_DOB)
        assert adapter._if_projector is None  # sem goals.if_meta

    def test_defaults_all_other_services(self):
        adapter = E5AnalyzerAdapter()
        # Todos os services defaults devem estar presentes.
        assert adapter._ratios is not None
        assert adapter._orcamento is not None
        assert adapter._endividamento is not None
        assert adapter._previdencia is not None
        assert adapter._inv_classes is not None
        assert adapter._consumo is not None
        assert adapter._equilibrio is not None
        assert adapter._diagnostico is not None
        assert adapter._pontos_fortes is not None
        assert adapter._pontos_urgentes is not None


class TestAnalyzeViaStore:
    def test_minimal_store_returns_result(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter.from_configs(
            goals={"independencia_financeira": {"if_meta": 5_000_000, "trs_pct": 4.0}},
            titular_dob=_DAVID_DOB,
        )

        result = adapter.analyze_via_store(store)

        assert isinstance(result, E5AnalysisResult)
        assert result.members is not None
        assert result.fluxo_enriched is not None
        assert result.ratios is not None

    def test_if_projection_populated_when_configured(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter.from_configs(
            goals={"independencia_financeira": {"if_meta": 5_000_000, "trs_pct": 4.0}},
            titular_dob=_DAVID_DOB,
        )

        result = adapter.analyze_via_store(store)

        assert result.if_projection is not None
        assert result.if_projection.if_meta == 5_000_000

    def test_if_projection_none_without_config(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()  # sem configs

        result = adapter.analyze_via_store(store)

        assert result.if_projection is None

    def test_ratios_uses_12m_window(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # 12m janela com 12 meses.
        assert result.ratios.janela_n_meses == 12
        # Receita 120k, despesa 60k → taxa total = 50%
        assert result.ratios.taxa_poupanca_total_pct == pytest.approx(50.0)

    def test_orcamento_divide_by_num_months(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # 60k / 12 = 5k total mensal
        assert result.orcamento.total == pytest.approx(5_000.0)

    def test_endividamento_computa_percentual(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # 200k dividas / 1.5M bruto = 13.33%
        assert result.endividamento.percentual_patrimonio == pytest.approx(13.33, rel=1e-2)

    def test_previdencia_nd_when_sem_receita_pj(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # por_fonte: {"receita_clt": 120_000} — sem PJ.
        assert result.previdencia.status == "N/D"

    def test_consumo_consciente_sem_pontuais(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # Valores R$3000-5000 abaixo do threshold default R$2000? ON: R$5000 ≥ 2000
        # Ah, MERCADO R$5000 ≥ R$2000 → é pontual.
        # Mas "mercado" NÃO está em RECURRENT_CATEGORIES default.
        # Moradia é. Mercado está em RECURRENT_CATEGORIES? Não — "moradia" sim.
        # Então mercado R$5000 é pontual.
        # Pelo menos um item.
        assert len(result.consumo_consciente.itens) >= 1

    def test_diagnostico_comportamental_populated(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # Sempre retorna ao menos 1 (fallback ou real).
        assert len(result.diagnosticos) >= 1

    def test_pontos_urgentes_inclui_seguro(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        acoes = {p.acao for p in result.pontos_urgentes}
        assert "Contratar seguro de vida e invalidez" in acoes

    def test_equilibrio_cerbasi_computed(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        assert result.equilibrio_cerbasi.pct_presente > 0

    def test_empty_store_returns_defaulted_result(self):
        store = InMemoryArtifactStore()
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # Todos os valores zerados mas sem exceção.
        assert result.fluxo_enriched.receita_total == 0
        assert result.ratios.taxa_poupanca_recorrente_pct == 0


class TestResultType:
    def test_result_is_frozen(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()
        result = adapter.analyze_via_store(store)

        # Frozen dataclass — não permite atribuição.
        with pytest.raises(Exception):
            result.receitas = {}  # type: ignore[misc]
