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
        cfg = FluxoEnricherConfig.from_categorization(
            {
                "one_time_income_categories": ["custom"],
                "one_time_income_keywords": ["CUSTOMKW"],
            }
        )
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
        meses = [f"2024-{m:02d}" for m in range(1, 13)] + [f"2025-{m:02d}" for m in range(1, 13)]
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
            "receita_total",
            "receita_recorrente",
            "receita_one_time",
            "receita_recorrente_mensal",
            "despesa_total",
            "despesa_mensal_media",
            "fluxo_liquido",
            "por_fonte",
            "receita_por_natureza",
            "por_fonte_detalhado",
            "despesas_por_categoria",
            "tabela_receitas",
            "receita_despesa_mensal_detalhado",
            "janela_12m",
        }
        assert required.issubset(d.keys())


class TestReceitaPorNatureza:
    """ADR-330: bloco derivado ``receita_por_natureza`` (fora de ``por_fonte``)."""

    def _enrich(self, por_categoria: dict) -> FluxoCaixaEnriched:
        total = round(sum(por_categoria.values()), 2)
        return FluxoCaixaEnricher().enrich(
            _receitas(total=total, por_categoria=por_categoria),
            _despesas(),
            _fluxo_mensal(["2026-01"], {}, {}),
        )

    def test_receita_pj_soma_pro_labore_e_lucros(self):
        nat = self._enrich(
            {
                "pro_labore": 3_000.0,
                "lucros_distribuidos": 4_000.0,
                "receita_clt": 3_000.0,
                "receita_aluguel": 1_500.0,
                "receita_investimento": 500.0,
            }
        ).to_legacy_dict()["receita_por_natureza"]
        assert nat["receita_pj"] == 7_000.0  # pro_labore + lucros_distribuidos
        assert nat["receita_clt"] == 3_000.0
        assert nat["receita_aluguel"] == 1_500.0
        assert nat["receita_outras"] == 500.0  # resíduo (receita_investimento)

    def test_das_iss_folha_nao_entram_em_receita_pj(self):
        # das_simples é DESPESA-PJ — se aparecer no bloco de receita, não conta como renda PJ.
        nat = self._enrich(
            {"pro_labore": 1_000.0, "das_simples": 500.0, "receita_clt": 1_000.0}
        ).to_legacy_dict()["receita_por_natureza"]
        assert nat["receita_pj"] == 1_000.0  # só pro_labore

    def test_conservacao_soma_igual_receita_total_em_cents(self):
        d = self._enrich(
            {
                "pro_labore": 1_234.56,
                "lucros_distribuidos": 2_345.67,
                "receita_clt": 3_456.78,
                "receita_aluguel": 987.65,
                "receita_resgate": 111.11,
            }
        ).to_legacy_dict()
        nat = d["receita_por_natureza"]

        def _c(v: float) -> int:
            return round(v * 100)

        assert sum(_c(v) for v in nat.values()) == _c(d["receita_total"])
        assert nat["receita_outras"] >= 0


class TestAporteTransferencia:
    """ADR-333: aporte_investimento é transferência patrimonial (poupança), não consumo."""

    def _janela(self, despesas_mes: dict) -> dict:
        r = FluxoCaixaEnricher().enrich(
            _receitas(total=10_000, por_categoria={"receita_clt": 10_000}),
            _despesas(total=10_000),
            _fluxo_mensal(
                ["2026-01"],
                {"2026-01": {"Salario": 10_000.0}},
                {"2026-01": despesas_mes},
            ),
        )
        return r.to_legacy_dict()["janela_12m"]

    def test_aporte_sai_do_consumo_e_eleva_poupanca(self):
        j = self._janela({"_total": 10_000.0, "aporte_investimento": 3_000.0, "mercado": 7_000.0})
        assert j["despesa_total"] == 10_000.0  # conservação: total inalterado
        assert j["transferencia_patrimonial"] == 3_000.0
        assert j["despesa_consumo"] == 7_000.0  # total − aporte
        assert j["fluxo_liquido"] == 0.0  # rec 10k − despesa_total 10k (conservação)
        assert j["taxa_poupanca_recorrente"] == 30.0  # (10k − consumo 7k)/10k; NÃO 0%

    def test_sem_aporte_consumo_igual_total(self):
        j = self._janela({"_total": 8_000.0, "mercado": 8_000.0})
        assert j["transferencia_patrimonial"] == 0.0
        assert j["despesa_consumo"] == j["despesa_total"] == 8_000.0
        assert j["taxa_poupanca_recorrente"] == 20.0  # (10k − 8k)/10k


class TestConsolidacaoCrossDocumento:
    """[[A40.l2]] PR3c1b — o contador do colapso atravessa E4→E5 e é projetado na janela 12m.
    É o número que a S2 declara à família ("N lançamentos consolidados por sobreposição de
    documentos, em M meses"); sem ele o agregado fica irreconciliável contra o extrato do
    banco — veto de adoção B2B2C, salvaguarda nº 1 do `financial-planner`."""

    @staticmethod
    def _e4(meses_ordenados: list[str], consolidacao: dict | None = None) -> dict:
        fluxo = {
            "meses_ordenados": meses_ordenados,
            "receitas": {"por_mes": {}},
            "despesas": {"por_mes": {}},
        }
        if consolidacao is not None:
            fluxo["consolidacao_cross_documento"] = consolidacao
        return fluxo

    def _legacy(self, meses_ordenados: list[str], consolidacao: dict | None = None) -> dict:
        e4 = self._e4(meses_ordenados, consolidacao)
        return (
            FluxoCaixaEnricher().enrich(receitas={}, despesas={}, fluxo_mensal=e4).to_legacy_dict()
        )

    def test_contador_do_e4_chega_em_fluxo_caixa(self):
        payload = {
            "count": 7,
            "meses": [{"mes": "2026-01", "count": 3}, {"mes": "2026-02", "count": 4}],
        }

        assert (
            self._legacy(["2026-01", "2026-02"], payload)["consolidacao_cross_documento"] == payload
        )

    def test_projecao_12m_conta_so_o_que_caiu_dentro_da_janela(self):
        meses = [f"2025-{m:02d}" for m in range(1, 13)] + ["2026-01", "2026-02"]
        payload = {
            "count": 11,
            "meses": [
                {"mes": "2024-12", "count": 4},  # antes da janela
                {"mes": "2025-06", "count": 3},
                {"mes": "2026-02", "count": 4},
            ],
        }

        legacy = self._legacy(meses, payload)

        assert legacy["consolidacao_cross_documento"]["count"] == 11  # corpus inteiro
        assert legacy["janela_12m"]["consolidacao_cross_documento"]["count"] == 7  # só a janela

    def test_projecao_e_por_INTERVALO_nao_por_pertinencia(self):
        """`meses_ordenados` vem das transações SOBREVIVENTES: um mês cujo movimento era
        majoritariamente a perna duplicada some da lista. Filtrar por pertinência descartaria
        a remoção que aconteceu DENTRO da janela — e o contador deixaria de reconciliar."""
        # 2025-06 NÃO está em `meses_ordenados`, mas está entre o primeiro e o último.
        meses = ["2025-01", "2025-12"]
        payload = {"count": 5, "meses": [{"mes": "2025-06", "count": 5}]}

        janela = self._legacy(meses, payload)["janela_12m"]["consolidacao_cross_documento"]

        assert janela is not None, "mês ausente de meses_ordenados sumiu da janela"
        assert janela["count"] == 5

    def test_campo_omitido_quando_o_e4_nao_tem_o_contador(self):
        """Omissão não é estética: o sha256 do E5 inteiro é chave de cache do parecer E do
        section summary da S2 — chave sempre presente regeraria os dois em toda a base."""
        legacy = self._legacy(["2026-01"])

        assert "consolidacao_cross_documento" not in legacy
        assert "consolidacao_cross_documento" not in legacy["janela_12m"]

    def test_count_zero_no_e4_tambem_omite(self):
        legacy = self._legacy(["2026-01"], {"count": 0, "meses": []})

        assert "consolidacao_cross_documento" not in legacy

    def test_janela_sem_remocao_dentro_dela_omite_mas_full_declara(self):
        meses = [f"2025-{m:02d}" for m in range(1, 13)] + ["2026-01", "2026-02"]
        payload = {"count": 4, "meses": [{"mes": "2024-12", "count": 4}]}

        legacy = self._legacy(meses, payload)

        assert legacy["consolidacao_cross_documento"]["count"] == 4
        assert "consolidacao_cross_documento" not in legacy["janela_12m"]

    @pytest.mark.parametrize("classe", [FluxoCaixaEnriched, Janela12m])
    def test_todo_campo_da_dataclass_e_emitido(self, classe):
        """As duas dataclasses são construídas campo-a-campo, então campo novo se perde em
        silêncio se o serializador não for atualizado. Derivar de `fields()` pega isso; a
        lista à mão não pega."""
        from dataclasses import fields

        payload = {"count": 1, "meses": [{"mes": "2026-01", "count": 1}]}
        legacy = self._legacy(["2026-01"], payload)
        emitido = legacy if classe is FluxoCaixaEnriched else legacy["janela_12m"]
        # `chart_*`/`por_fonte*`/`tabela_receitas` são remapeados para outros nomes no dict
        # legado; o campo novo não é, então basta afirmar que ele aparece.
        assert "consolidacao_cross_documento" in {f.name for f in fields(classe)}
        assert "consolidacao_cross_documento" in emitido
