"""Tests — ``FluxoCaixaEnricher`` (Sessão A5c)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.fluxo_caixa_enricher import (  # noqa: E402
    FluxoCaixaEnriched,
    FluxoCaixaEnricher,
    FluxoEnricherConfig,
    Janela12m,
)


def _receitas(
    total: float = 100_000,
    por_categoria: dict | None = None,
    dados: dict | None = None,
) -> dict:
    return {
        "total_geral": total,
        "totais_por_categoria": por_categoria or {"receita_clt": total},
        "dados": dados or {},
    }


def _despesas(total: float = 60_000, por_categoria: dict | None = None) -> dict:
    return {
        "total_geral": total,
        "totais_por_categoria": por_categoria or {"mercado": 40_000, "uber": 20_000},
    }


def _fluxo_mensal(meses: list[str], receitas_por_mes: dict, despesas_por_mes: dict) -> dict:
    return {
        "meses_ordenados": meses,
        "receitas": {"por_mes": receitas_por_mes},
        "despesas": {"por_mes": despesas_por_mes},
    }


class TestConfig:
    def test_defaults_include_one_time_categories(self):
        cfg = FluxoEnricherConfig()
        assert "receita_resgate" in cfg.one_time_categories
        assert "receita_fgts" in cfg.one_time_categories

    def test_from_categorization_overrides(self):
        cfg = FluxoEnricherConfig.from_categorization({
            "one_time_income_categories": ["custom"],
            "one_time_income_keywords": ["CUSTOMKW"],
        })
        assert cfg.one_time_categories == frozenset({"custom"})
        assert cfg.one_time_keywords == ("customkw",)


class TestSplitReceita:
    def test_categoria_inteira_marcada_one_time(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(
                total=10_000,
                dados={
                    "receita_resgate": [{"valor": 3_000}],
                    "receita_clt": [{"valor": 7_000}],
                },
            ),
            _despesas(total=0),
            _fluxo_mensal(["2026-01"], {}, {}),
        )
        assert r.receita_one_time == 3_000
        assert r.receita_recorrente == 7_000

    def test_descricao_keyword_marca_individual(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(
                total=10_000,
                dados={
                    "receita_clt": [
                        {"valor": 6_000, "descricao": "SALARIO"},
                        {"valor": 4_000, "descricao": "RESTITUICAO IR 2024"},
                    ],
                },
            ),
            _despesas(total=0),
            _fluxo_mensal(["2026-01"], {}, {}),
        )
        assert r.receita_one_time == 4_000
        assert r.receita_recorrente == 6_000

    def test_sem_one_time_mantem_total_como_recorrente(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(total=10_000),
            _despesas(total=0),
            _fluxo_mensal(["2026-01"], {}, {}),
        )
        assert r.receita_one_time == 0
        assert r.receita_recorrente == 10_000


class TestMedias:
    def test_receita_recorrente_mensal(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(total=120_000),
            _despesas(total=60_000),
            _fluxo_mensal(
                [f"2026-{m:02d}" for m in range(1, 13)],
                {},
                {},
            ),
        )
        assert r.receita_recorrente_mensal == 10_000
        assert r.despesa_mensal_media == 5_000

    def test_num_months_zero_usa_fallback_1(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(total=1000),
            _despesas(total=500),
            _fluxo_mensal([], {}, {}),
        )
        # Fallback num_months=1 → médias iguais aos totais.
        assert r.receita_recorrente_mensal == 1000
        assert r.despesa_mensal_media == 500


class TestFluxoLiquido:
    def test_positivo(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(total=100),
            _despesas(total=60),
            _fluxo_mensal(["2026-01"], {}, {}),
        )
        assert r.fluxo_liquido == 40


class TestTabelaReceitas:
    def test_ordenada_por_valor_desc_com_pct(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(
                total=100_000,
                por_categoria={"receita_clt": 80_000, "receita_aluguel": 20_000},
            ),
            _despesas(total=0),
            _fluxo_mensal(["2026-01"], {}, {}),
        )
        labels = [t["categoria"] for t in r.tabela_receitas]
        assert labels[0] == "Receita Clt"  # 80%
        assert r.tabela_receitas[0]["pct"] == 80.0
        assert r.tabela_receitas[1]["pct"] == 20.0


class TestChartDatasets:
    def test_labels_format_YY_MM(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(),
            _despesas(),
            _fluxo_mensal(["2026-01", "2026-02"], {}, {}),
        )
        assert r.chart_labels == ("26/01", "26/02")

    def test_receita_datasets_por_origem(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(),
            _despesas(total=0),
            _fluxo_mensal(
                ["2026-01", "2026-02"],
                {
                    "2026-01": {"Empregador A": 5000, "_total": 5000},
                    "2026-02": {"Empregador A": 5500, "_total": 5500},
                },
                {},
            ),
        )
        labels = [d["label"] for d in r.chart_receita_datasets]
        assert "Empregador A" in labels

    def test_skip_dataset_sem_valor(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(),
            _despesas(total=0),
            _fluxo_mensal(
                ["2026-01"],
                {"2026-01": {"Empregador A": 0, "_total": 0}},
                {},
            ),
        )
        assert r.chart_receita_datasets == ()


class TestJanela12m:
    def test_cap_em_12_meses(self):
        meses = [f"2024-{m:02d}" for m in range(1, 13)] + [
            f"2025-{m:02d}" for m in range(1, 13)
        ]
        # 24 meses → janela deve pegar só os últimos 12.
        receita_por_mes = {m: {"Empregador A": 5000, "_total": 5000} for m in meses}
        r = FluxoCaixaEnricher().enrich(
            _receitas(),
            _despesas(total=0),
            _fluxo_mensal(meses, receita_por_mes, {m: {"_total": 1000} for m in meses}),
        )
        assert r.janela_12m.n_meses == 12
        assert r.janela_12m.receita_total == 60_000  # 12 × 5000
        assert r.janela_12m.periodo == "2025-01 a 2025-12"

    def test_menos_de_12_meses_usa_tudo(self):
        meses = [f"2026-{m:02d}" for m in range(1, 7)]  # 6 meses
        receita_por_mes = {m: {"Empregador A": 3000, "_total": 3000} for m in meses}
        r = FluxoCaixaEnricher().enrich(
            _receitas(),
            _despesas(),
            _fluxo_mensal(meses, receita_por_mes, {m: {"_total": 1000} for m in meses}),
        )
        assert r.janela_12m.n_meses == 6

    def test_one_time_origem_excluida_de_recorrente(self):
        meses = ["2026-01"]
        receita_por_mes = {
            "2026-01": {"Empregador A": 5000, "Resgates": 2000, "_total": 7000},
        }
        r = FluxoCaixaEnricher().enrich(
            _receitas(),
            _despesas(total=0),
            _fluxo_mensal(meses, receita_por_mes, {}),
        )
        assert r.janela_12m.receita_total == 7000
        assert r.janela_12m.receita_recorrente == 5000
        assert r.janela_12m.receita_one_time == 2000

    def test_taxa_poupanca_recorrente(self):
        meses = ["2026-01"]
        rpm = {"2026-01": {"Empregador A": 10_000, "_total": 10_000}}
        dpm = {"2026-01": {"_total": 6000}}
        r = FluxoCaixaEnricher().enrich(
            _receitas(),
            _despesas(),
            _fluxo_mensal(meses, rpm, dpm),
        )
        # (10k - 6k) / 10k = 40%
        assert r.janela_12m.taxa_poupanca_recorrente == 40.0


class TestPorFonteDetalhado:
    def test_agrega_receitas_por_origem_na_janela(self):
        meses = ["2026-01", "2026-02"]
        rpm = {
            "2026-01": {"Empregador A": 5000, "Aluguéis": 1000, "_total": 6000},
            "2026-02": {"Empregador A": 5500, "Aluguéis": 1000, "_total": 6500},
        }
        r = FluxoCaixaEnricher().enrich(
            _receitas(),
            _despesas(),
            _fluxo_mensal(meses, rpm, {m: {"_total": 1000} for m in meses}),
        )
        assert r.por_fonte_detalhado["Empregador A"] == 10_500
        assert r.por_fonte_detalhado["Aluguéis"] == 2000


class TestResult:
    def test_result_is_frozen(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(), _despesas(), _fluxo_mensal(["2026-01"], {}, {})
        )
        assert isinstance(r, FluxoCaixaEnriched)
        assert isinstance(r.janela_12m, Janela12m)

    def test_legacy_dict_has_all_required_fields(self):
        r = FluxoCaixaEnricher().enrich(
            _receitas(), _despesas(), _fluxo_mensal(["2026-01"], {}, {})
        )
        d = r.to_legacy_dict()
        required = {
            "receita_total", "receita_recorrente", "receita_one_time",
            "receita_recorrente_mensal", "despesa_total", "despesa_mensal_media",
            "fluxo_liquido", "por_fonte", "por_fonte_detalhado",
            "despesas_por_categoria", "tabela_receitas",
            "receita_despesa_mensal_detalhado", "janela_12m",
        }
        assert required.issubset(d.keys())
