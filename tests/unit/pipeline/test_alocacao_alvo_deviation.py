"""Testes do AlocacaoAlvoDeviationCalculator (ADR-141 §Emenda 2026-07-08)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.alocacao_alvo_deviation import (
    COMPARABLE_KEYS,
    AlocacaoAlvoDeviationCalculator,
    severity_for_desvio,
)

CALC = AlocacaoAlvoDeviationCalculator()

ALVO_V2_PADRAO = {
    "rf_pos_pct": 20,
    "rf_pre_pct": 10,
    "rf_ipca_pct": 10,
    "acoes_br_pct": 25,
    "acoes_int_pct": 15,
    "fiis_pct": 10,
    "caixa_pct": 10,
}


def _classe(categoria: str, quantia: float) -> dict:
    # fixture JSON-like: shape do to_dict de ClasseAtivo (float no wire)
    return {"categoria": categoria, "valor": quantia, "pct": 0.0}


class TestSeverity:
    def test_thresholds_canonicos(self):
        assert severity_for_desvio(0.0) == "alinhado"
        assert severity_for_desvio(-2.0) == "alinhado"
        assert severity_for_desvio(2.01) == "atencao"
        assert severity_for_desvio(-5.0) == "atencao"
        assert severity_for_desvio(5.01) == "rebalancear"

    def test_sem_alvo_e_neutro(self):
        assert severity_for_desvio(None) == "neutro"


class TestMapping10Para7:
    def test_previdencia_agrega_em_renda_fixa(self):
        result = CALC.calculate(
            [_classe("Renda Fixa", 600.0), _classe("Previdência", 400.0)],
            ALVO_V2_PADRAO,
        )
        rf = next(r for r in result.comparaveis if r.classe == "renda_fixa")
        assert rf.valor_brl == Decimal("1000.0")
        assert set(rf.componentes) == {"Renda Fixa", "Previdência"}

    def test_fundos_agregam_em_acoes_br(self):
        result = CALC.calculate(
            [_classe("Ações BR", 300.0), _classe("Fundos", 200.0)], ALVO_V2_PADRAO
        )
        acoes = next(r for r in result.comparaveis if r.classe == "acoes_br")
        assert acoes.valor_brl == Decimal("500.0")

    def test_cripto_e_outros_vao_para_fora_alvo_com_alvo_zero(self):
        result = CALC.calculate(
            [_classe("Renda Fixa", 900.0), _classe("Cripto", 50.0), _classe("Outros", 50.0)],
            ALVO_V2_PADRAO,
        )
        fora = next(r for r in result.comparaveis if r.classe == "fora_alvo")
        assert fora.alvo_pct == 0.0
        assert fora.desvio_pp == pytest.approx(10.0)
        assert fora.severity == "rebalancear"

    def test_imoveis_investimento_fora_da_carteira_liquida(self):
        result = CALC.calculate(
            [_classe("Renda Fixa", 1000.0), _classe("Imóveis Investimento", 3000.0)],
            ALVO_V2_PADRAO,
        )
        assert result.imoveis_fisicos_brl == Decimal("3000.0")
        assert result.carteira_liquida_brl == Decimal("1000.0")
        rf = next(r for r in result.comparaveis if r.classe == "renda_fixa")
        assert rf.atual_pct == pytest.approx(100.0)

    def test_caixa_fora_da_carteira_liquida(self):
        result = CALC.calculate(
            [_classe("Renda Fixa", 800.0), _classe("Caixa", 200.0)], ALVO_V2_PADRAO
        )
        assert result.carteira_liquida_brl == Decimal("800.0")
        assert result.caixa.valor_brl == Decimal("200.0")


class TestRenormalizacaoSemCaixa:
    def test_alvos_renormalizados_pela_soma_de_investimento(self):
        # caixa_pct=10 → RF 40/90, acoes_br 25/90 etc.
        result = CALC.calculate([_classe("Renda Fixa", 100.0)], ALVO_V2_PADRAO)
        rf = next(r for r in result.comparaveis if r.classe == "renda_fixa")
        assert rf.alvo_pct == pytest.approx(40 / 90 * 100)

    def test_caixa_pct_100_desvios_null(self):
        result = CALC.calculate(
            [_classe("Renda Fixa", 100.0)],
            {"caixa_pct": 100},
        )
        assert result.has_alvo is True
        rf = next(r for r in result.comparaveis if r.classe == "renda_fixa")
        assert rf.alvo_pct is None
        assert rf.desvio_pp is None
        assert result.desvio_max_pct is None

    def test_soma_diferente_de_100_renormaliza_defensivo_com_flag(self):
        alvo = {"rf_pos_pct": 30, "acoes_br_pct": 30}  # soma 60 ≠ 100
        result = CALC.calculate([_classe("Renda Fixa", 50.0), _classe("Ações BR", 50.0)], alvo)
        assert result.alvo_renormalizado_defensivo is True
        rf = next(r for r in result.comparaveis if r.classe == "renda_fixa")
        assert rf.alvo_pct == pytest.approx(50.0)

    def test_soma_100_nao_marca_defensivo(self):
        result = CALC.calculate([_classe("Renda Fixa", 100.0)], ALVO_V2_PADRAO)
        assert result.alvo_renormalizado_defensivo is False


class TestDesvioENextAporte:
    def test_desvio_assinado_negativo_subalocada(self):
        # 100% RF: acoes_br está 0% vs alvo ~27.8% → desvio negativo.
        result = CALC.calculate([_classe("Renda Fixa", 1000.0)], ALVO_V2_PADRAO)
        acoes = next(r for r in result.comparaveis if r.classe == "acoes_br")
        assert acoes.desvio_pp < 0

    def test_next_aporte_classe_mais_subalocada(self):
        result = CALC.calculate([_classe("Renda Fixa", 1000.0)], ALVO_V2_PADRAO)
        assert result.next_aporte_classe == "acoes_br"

    def test_next_aporte_tie_break_ordem_canonica(self):
        # acoes_br e acoes_int igualmente subalocadas → vence acoes_br (ordem canônica).
        alvo = {"rf_pos_pct": 50, "acoes_br_pct": 25, "acoes_int_pct": 25}
        result = CALC.calculate([_classe("Renda Fixa", 1000.0)], alvo)
        assert result.next_aporte_classe == "acoes_br"
        assert COMPARABLE_KEYS.index("acoes_br") < COMPARABLE_KEYS.index("acoes_int")

    def test_fora_alvo_nunca_recebe_aporte(self):
        # fora_alvo tem desvio 0 (sem posição), nunca negativo — mas mesmo
        # que o alvo declare tudo em RF já alocada, fora_alvo não entra.
        alvo = {"rf_pos_pct": 100}
        result = CALC.calculate([_classe("Renda Fixa", 1000.0)], alvo)
        assert result.next_aporte_classe is None

    def test_desvio_max_inclui_fora_alvo(self):
        alvo = {"rf_pos_pct": 100}
        result = CALC.calculate([_classe("Renda Fixa", 500.0), _classe("Cripto", 500.0)], alvo)
        assert result.desvio_max_pct == pytest.approx(50.0)

    def test_ordenacao_por_desvio_absoluto_desc(self):
        result = CALC.calculate([_classe("Renda Fixa", 1000.0)], ALVO_V2_PADRAO)
        desvios = [abs(r.desvio_pp) for r in result.comparaveis if r.desvio_pp is not None]
        assert desvios == sorted(desvios, reverse=True)


class TestSinalExcessoCaixa:
    CARTEIRA = [_classe("Renda Fixa", 500.0), _classe("Caixa", 500.0)]

    def test_excesso_computado_quando_atual_acima_do_alvo(self):
        result = CALC.calculate(self.CARTEIRA, ALVO_V2_PADRAO, reserva_completa=True)
        assert result.caixa.excesso_pp == pytest.approx(40.0)
        assert result.caixa.sinal_excesso is True

    def test_reserva_incompleta_silencia_sinal(self):
        result = CALC.calculate(self.CARTEIRA, ALVO_V2_PADRAO, reserva_completa=False)
        assert result.caixa.excesso_pp == pytest.approx(40.0)
        assert result.caixa.sinal_excesso is False

    def test_reserva_desconhecida_silencia_sinal(self):
        result = CALC.calculate(self.CARTEIRA, ALVO_V2_PADRAO)
        assert result.caixa.sinal_excesso is False

    def test_caixa_abaixo_do_alvo_sem_excesso(self):
        carteira = [_classe("Renda Fixa", 950.0), _classe("Caixa", 50.0)]
        result = CALC.calculate(carteira, ALVO_V2_PADRAO, reserva_completa=True)
        assert result.caixa.excesso_pp is None
        assert result.caixa.sinal_excesso is False


class TestSemAlvo:
    def test_sem_alvo_desvios_null_e_severity_neutro(self):
        result = CALC.calculate([_classe("Renda Fixa", 1000.0)], None)
        assert result.has_alvo is False
        assert result.desvio_max_pct is None
        assert result.next_aporte_classe is None
        assert all(r.severity == "neutro" for r in result.comparaveis)

    def test_carteira_vazia_nao_quebra(self):
        result = CALC.calculate([], ALVO_V2_PADRAO)
        assert result.carteira_liquida_brl == Decimal("0")
        assert result.desvio_max_pct is not None  # alvo declarado, atual 0


class TestContratoToDict:
    def test_leaves_monetarias_com_sufixo_brl_e_percentuais_com_pct_ou_pp(self):
        result = CALC.calculate(
            [_classe("Renda Fixa", 1000.0), _classe("Caixa", 100.0)], ALVO_V2_PADRAO
        ).to_dict()
        assert "carteira_liquida_brl" in result
        assert "imoveis_fisicos_brl" in result
        assert "valor_brl" in result["comparaveis"][0]
        assert "valor_brl" in result["caixa"]
        assert result["rf_comparacao"] == "agregada"

    def test_valores_arredondados_2_casas(self):
        result = CALC.calculate([_classe("Renda Fixa", 333.333)], ALVO_V2_PADRAO).to_dict()
        assert result["carteira_liquida_brl"] == 333.33

    def test_ignora_valores_negativos_e_categorias_desconhecidas(self):
        result = CALC.calculate(
            [_classe("Renda Fixa", -10.0), _classe("Inexistente", 500.0)], ALVO_V2_PADRAO
        )
        assert result.carteira_liquida_brl == Decimal("0")
