"""Tests — ``PassiveIncomeCalculator`` core (Lane A8.3 PR-A): buckets + status."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer
from pipeline.domain.services.passive_income_calculator import (
    DistribuicaoPJSignal,
    PassiveIncomeConfig,
    PassiveIncomeResult,
)
from pipeline.llm.schemas.e16_irpf_full import (
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
)
from tests.unit.pipeline._passive_income_builders import (
    bem,
    calc,
    decl,
    exclusiva,
    exterior_rend,
    isento,
    patrimonio,
)

_REF_DATE = date(2025, 6, 1)
_NO_DESPESA = Decimal("0")


# ---------------------------------------------------------------------------
# Bucket — cada fonte IRPF
# ---------------------------------------------------------------------------


class TestRendaPassivaPorFonte:
    def test_dividendos_cod_09_isento(self):
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "10000.00")])
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.status == "ok"
        assert result.renda_passiva_por_fonte_brl["dividendos"] == Decimal("10000.00")
        assert result.renda_passiva_anual_brl == Decimal("10000.00")

    def test_jcp_cod_10_exclusiva(self):
        d = decl(exclusiva_list=[exclusiva(CodigoRendimentoTribExclusiva.jcp, "5000.00")])
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.renda_passiva_por_fonte_brl["jcp"] == Decimal("5000.00")

    def test_aplicacoes_cod_12_isento_e_exclusiva(self):
        # cod 12 isento (pensao recebida usa value="12") + cod 12 exclusiva
        d = decl(
            isentos=[isento(CodigoRendimentoIsento.pensao_alimenticia_recebida, "1000")],
            exclusiva_list=[
                exclusiva(
                    CodigoRendimentoTribExclusiva.rendimentos_aplicacoes_financeiras,
                    "3000.00",
                )
            ],
        )
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.renda_passiva_por_fonte_brl["aplicacoes"] == Decimal("4000.00")

    def test_ganho_capital_cod_06_exclusiva(self):
        d = decl(
            exclusiva_list=[exclusiva(CodigoRendimentoTribExclusiva.ganho_capital, "20000.00")]
        )
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.ganho_capital_excluido_brl == Decimal("20000.00")

    def test_exterior(self):
        d = decl(exterior=[exterior_rend("8000.00")])
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.renda_passiva_por_fonte_brl["exterior"] == Decimal("8000.00")

    def test_alugueis_zero_em_pra_paralelo_com_pr_b(self):
        # PR-A: bucket alugueis=0; PR-B realocará. Delta absorve no merge.
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "1000.00")])
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.renda_passiva_por_fonte_brl["alugueis"] == Decimal("0")


# ---------------------------------------------------------------------------
# A28.l2 — universo consistente (ADR-191): distribuição PJ do titular ≠ yield
# ---------------------------------------------------------------------------


_QUOTA_BEM = "QUOTAS DA EMPRESA ACME SERVICOS LTDA CNPJ 12.345.678/0001-90"


def _calc_with(decl_, **patrimonio_kwargs):
    return calc().calculate(
        irpf=IRPFAnalyzer([decl_]),
        patrimonio=patrimonio(**patrimonio_kwargs),
        investimentos_atuais=None,
        reference_date=_REF_DATE,
        despesa_mensal_media_brl=_NO_DESPESA,
    )


def _decl_dogfood():
    return decl(
        isentos=[
            isento(
                CodigoRendimentoIsento.lucros_dividendos,
                "284000.00",
                fonte="12.345.678/0001-90 ACME SERVICOS LTDA",
            ),
            isento(CodigoRendimentoIsento.lucros_dividendos, "12000.00"),
        ],
        exclusiva_list=[exclusiva(CodigoRendimentoTribExclusiva.jcp, "30000.00")],
        bens=[bem(descricao=_QUOTA_BEM)],
    )


class TestDistribuicaoPjTitular:
    def test_dividendo_da_pj_do_titular_sai_da_trs_por_cnpj(self):
        d = decl(
            isentos=[
                isento(
                    CodigoRendimentoIsento.lucros_dividendos,
                    "284000.00",
                    fonte="12.345.678/0001-90 ACME SERVICOS LTDA",
                    descricao="Lucros e dividendos recebidos",
                )
            ],
            bens=[bem(descricao=_QUOTA_BEM)],
        )
        result = _calc_with(d, investimentos_titular=500_000.0)
        assert result.renda_ativa_pj_excluida_brl == Decimal("284000.00")
        assert "distribuicao_pj_titular" not in result.renda_passiva_por_fonte_brl
        assert result.renda_passiva_por_fonte_brl["dividendos"] == Decimal("0")
        assert result.renda_passiva_anual_brl == Decimal("0")
        assert result.trs_efetiva_pct == Decimal("0.00")

    def test_dividendo_da_pj_do_titular_sai_da_trs_por_nome(self):
        d = decl(
            isentos=[
                isento(
                    CodigoRendimentoIsento.lucros_dividendos,
                    "50000.00",
                    descricao="Distribuição de lucros ACME SERVICOS LTDA",
                )
            ],
            bens=[bem(codigo="99", descricao=_QUOTA_BEM)],
        )
        result = _calc_with(d, investimentos_titular=500_000.0)
        assert result.renda_ativa_pj_excluida_brl == Decimal("50000.00")
        assert result.renda_passiva_anual_brl == Decimal("0")

    def test_dividendo_de_posicao_de_carteira_permanece_na_trs(self):
        # Ação listada em bens (cod 31) NÃO é participação societária — o
        # dividendo dela é yield de carteira e conta na TRS.
        d = decl(
            isentos=[
                isento(
                    CodigoRendimentoIsento.lucros_dividendos,
                    "10000.00",
                    fonte="61.532.644/0001-15 ITAUSA S.A.",
                )
            ],
            bens=[
                bem(codigo="31", descricao="ACOES ITSA4 ITAUSA S.A."),
                bem(descricao=_QUOTA_BEM),
            ],
        )
        result = _calc_with(d, investimentos_titular=500_000.0)
        assert result.renda_passiva_por_fonte_brl["dividendos"] == Decimal("10000.00")
        assert result.renda_ativa_pj_excluida_brl == Decimal("0")
        assert result.renda_passiva_anual_brl == Decimal("10000.00")

    def test_distribuicao_pj_nao_vaza_para_bucket_alugueis(self):
        # split_trabalho_vs_capital inclui todo cod-09 no capital; o delta
        # residual (aluguéis) precisa descontar também a distribuição PJ.
        d = decl(
            isentos=[
                isento(
                    CodigoRendimentoIsento.lucros_dividendos,
                    "284000.00",
                    fonte="12.345.678/0001-90 ACME SERVICOS LTDA",
                )
            ],
            bens=[bem(descricao=_QUOTA_BEM)],
        )
        result = _calc_with(d, investimentos_titular=500_000.0)
        assert result.renda_passiva_por_fonte_brl["alugueis"] == Decimal("0")

    def test_cenario_dogfood_trs_volta_a_plausivel(self):
        # Regressão do dogfood 72883bde: R$ 284k de distribuição PJ sobre
        # denominador de R$ 1,44M inflava TRS a 22,63%. Com o split, só o
        # yield de carteira (R$ 42k) sobre o universo casado entra.
        result = _calc_with(
            _decl_dogfood(), investimentos_titular=1_000_000.0, imoveis_investimento=1_440_000.0
        )
        assert result.renda_passiva_anual_brl == Decimal("42000.00")
        # 42k / 2,44M = 1,72% — plausível (< 8%)
        assert result.trs_efetiva_pct < Decimal("8.0")
        assert result.renda_ativa_pj_excluida_brl == Decimal("284000.00")


def _calc_signal(decl_, signal, **patrimonio_kwargs):
    return calc().calculate(
        irpf=IRPFAnalyzer([decl_]),
        patrimonio=patrimonio(**patrimonio_kwargs),
        investimentos_atuais=None,
        reference_date=_REF_DATE,
        despesa_mensal_media_brl=_NO_DESPESA,
        distribuicao_pj_signal=signal,
    )


class TestElevacaoPorSinalDeFluxo:
    """ADR-336: 2º sinal (fluxo lucros_distribuidos) eleva distribuição PJ quando o match IRPF falha."""

    def test_eleva_distribuicao_quando_match_irpf_falha(self):
        # cod-09 sem quota casável (matched=0) — o match por-linha não pega.
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "284000.00")])
        result = _calc_signal(
            d, DistribuicaoPJSignal(Decimal("308000.00"), 12), investimentos_titular=500_000.0
        )
        assert result.renda_ativa_pj_excluida_brl == Decimal("284000.00")
        assert result.renda_passiva_por_fonte_brl["dividendos"] == Decimal("0")
        assert result.renda_passiva_anual_brl == Decimal("0")

    def test_capa_no_cod09_declarado(self):
        # sinal do fluxo > cod-09 → nunca fabrica distribuição além do declarado.
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "284000.00")])
        result = _calc_signal(
            d, DistribuicaoPJSignal(Decimal("500000.00"), 12), investimentos_titular=500_000.0
        )
        assert result.renda_ativa_pj_excluida_brl == Decimal("284000.00")
        assert result.renda_passiva_por_fonte_brl["dividendos"] == Decimal("0")

    def test_respeita_piso_do_match_irpf(self):
        # match IRPF já achou 284k; sinal BAIXO não reduz (só eleva).
        d = decl(
            isentos=[
                isento(
                    CodigoRendimentoIsento.lucros_dividendos,
                    "284000.00",
                    fonte="12.345.678/0001-90 ACME SERVICOS LTDA",
                )
            ],
            bens=[bem(descricao=_QUOTA_BEM)],
        )
        result = _calc_signal(
            d, DistribuicaoPJSignal(Decimal("100000.00"), 12), investimentos_titular=500_000.0
        )
        assert result.renda_ativa_pj_excluida_brl == Decimal("284000.00")

    def test_sinal_none_e_bit_identico(self):
        # sem sinal → comportamento idêntico ao match por-linha (compat).
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "284000.00")])
        com_none = _calc_signal(d, None, investimentos_titular=500_000.0)
        sem_param = _calc_with(d, investimentos_titular=500_000.0)
        assert com_none.renda_passiva_por_fonte_brl == sem_param.renda_passiva_por_fonte_brl
        assert com_none.renda_ativa_pj_excluida_brl == sem_param.renda_ativa_pj_excluida_brl


class TestGanhoCapitalForaDaTRS:
    """ADR-336: ganho_capital (realização one-time) sai do numerador da TRS, mas fica visível."""

    def test_ganho_capital_visivel_mas_fora_do_numerador(self):
        d = decl(
            isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "10000.00")],
            exclusiva_list=[exclusiva(CodigoRendimentoTribExclusiva.ganho_capital, "50000.00")],
        )
        result = _calc_with(d, investimentos_titular=500_000.0)
        fontes = result.renda_passiva_por_fonte_brl
        assert result.ganho_capital_excluido_brl == Decimal("50000.00")  # visível (transparência)
        assert "ganho_capital" not in fontes  # A37.l7 PR-2: fora do dict conservativo
        assert fontes["alugueis"] == Decimal("0")  # não vaza p/ aluguéis (delta ajustado)
        assert result.renda_passiva_anual_brl == Decimal(
            "10000.00"
        )  # só o dividendo, sem ganho_capital


class TestUniversoConsistente:
    def test_denominador_soma_chaves_dinamicas_por_membro(self):
        # Regressão dogfood: PatrimonioCalculator emite ``investimentos_<nome>``
        # (ex.: investimentos_ana) — o denominador precisa incluí-las, senão a
        # TRS sai sobre "só imóveis geradores" enquanto o numerador tem
        # dividendos/JCP de carteira (universos diferentes, ADR-191).
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "10000.00")])
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio={
                "investimentos_ana": 400_000.0,
                "investimentos_bruno": 100_000.0,
                "imoveis_investimento": 500_000.0,
            },
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.patrimonio_gerador_brl == Decimal("1000000.0")
        assert result.trs_efetiva_pct == Decimal("1.00")


# ---------------------------------------------------------------------------
# Status enum + casos extremos
# ---------------------------------------------------------------------------


class TestStatus:
    def test_sem_irpf_quando_analyzer_none(self):
        result = calc().calculate(
            irpf=None,
            patrimonio=patrimonio(investimentos_titular=500_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=Decimal("5000"),
        )
        assert result.status == "sem_irpf"
        assert result.renda_passiva_anual_brl == Decimal("0")
        assert result.patrimonio_gerador_brl == Decimal("0")
        assert result.ano_referencia_irpf is None

    def test_sem_irpf_quando_analyzer_sem_anos(self):
        result = calc().calculate(
            irpf=IRPFAnalyzer([]),
            patrimonio=patrimonio(investimentos_titular=500_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=Decimal("5000"),
        )
        assert result.status == "sem_irpf"

    def test_gerador_zero_workspace_so_residencia(self):
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "1000.00")])
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(
                investimentos_titular=0.0, residencia=2_000_000.0, veiculos=100_000.0
            ),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=Decimal("5000"),
        )
        assert result.status == "gerador_zero"
        assert result.patrimonio_gerador_brl == Decimal("0")
        assert result.trs_efetiva_pct == Decimal("0")

    def test_ok_quando_irpf_e_gerador_positivos(self):
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "10000.00")])
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(investimentos_titular=500_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.status == "ok"
        assert result.trs_efetiva_pct == Decimal("2.00")


# ---------------------------------------------------------------------------
# Multi-membro
# ---------------------------------------------------------------------------


class TestMultiMembro:
    def test_titular_e_conjuge_somam_no_gerador(self):
        decl_t = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "5000.00")])
        decl_c = decl(exclusiva_list=[exclusiva(CodigoRendimentoTribExclusiva.jcp, "3000.00")])
        result = calc().calculate(
            irpf=IRPFAnalyzer([decl_t, decl_c]),
            patrimonio=patrimonio(investimentos_titular=400_000.0, investimentos_conjuge=200_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.patrimonio_gerador_brl == Decimal("600000.0")
        assert result.renda_passiva_anual_brl == Decimal("8000.00")
        # 8k / 600k * 100 = 1,33...
        assert result.trs_efetiva_pct == Decimal("1.33")


# ---------------------------------------------------------------------------
# Decimal everywhere (ADR-090) + escolha de ano-base
# ---------------------------------------------------------------------------


class TestDecimalEverywhere:
    def test_todos_campos_money_sao_decimal(self):
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "10000.00")])
        result: PassiveIncomeResult = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(investimentos_titular=500_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        for v in (
            result.renda_passiva_anual_brl,
            result.renda_passiva_mensal_brl,
            result.renda_ativa_pj_excluida_brl,
            result.ganho_capital_excluido_brl,
            result.patrimonio_gerador_brl,
            result.trs_efetiva_pct,
            result.acumuladores_pct_gerador,
            *result.renda_passiva_por_fonte_brl.values(),
        ):
            assert isinstance(v, Decimal)

    def test_acumuladores_matching_por_token_nao_inicial(self):
        """ADR-306 — descrição IRPF embute ticker no meio ("1000 ACOES BOVA11...");
        matching primeiro-token zerava ``acumuladores_pct_gerador`` no dogfood."""
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "10000.00")])
        inv = {
            "dados": [
                {"nome": "1000 ACOES DE BOVA11 - ISHARES IBOVESPA", "valor_atual": 100_000},
            ]
        }
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(investimentos_titular=500_000.0),
            investimentos_atuais=inv,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        # 100k / 500k = 20% do gerador em acumuladores.
        assert result.acumuladores_pct_gerador == Decimal("20.00")

    def test_mensal_eh_anual_dividido_por_12(self):
        d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "12000.00")])
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(investimentos_titular=200_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.renda_passiva_mensal_brl == Decimal("1000")


def test_selecionar_ultimo_ano_base_quando_multiplos():
    decl_old = decl(
        ano_base=2022,
        isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "5000.00")],
    )
    decl_new = decl(
        ano_base=2024,
        isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "12000.00")],
    )
    result = calc().calculate(
        irpf=IRPFAnalyzer([decl_old, decl_new]),
        patrimonio=patrimonio(investimentos_titular=300_000.0),
        investimentos_atuais=None,
        reference_date=_REF_DATE,
        despesa_mensal_media_brl=_NO_DESPESA,
    )
    assert result.ano_referencia_irpf == 2024
    assert result.renda_passiva_anual_brl == Decimal("12000.00")


def test_float_no_patrimonio_eh_coercido_via_str():
    # PatrimonioCalculator emite floats hoje (legado A6d); calculator
    # converte via Decimal(str(v)) — boundary ADR-090.
    d = decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "1000.00")])
    result = calc().calculate(
        irpf=IRPFAnalyzer([d]),
        patrimonio={"investimentos_titular": 500_000.50},
        investimentos_atuais=None,
        reference_date=_REF_DATE,
        despesa_mensal_media_brl=_NO_DESPESA,
    )
    assert result.patrimonio_gerador_brl == Decimal("500000.5")


def _smoke_decl():
    return decl(
        isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "20000.00")],
        exclusiva_list=[
            exclusiva(CodigoRendimentoTribExclusiva.jcp, "10000.00"),
            exclusiva(
                CodigoRendimentoTribExclusiva.rendimentos_aplicacoes_financeiras,
                "8000.00",
            ),
        ],
    )


def test_smoke_renda_passiva_e_trs_efetiva_sensata():
    # Cenário-tipo dogfood: TRS efetiva sai entre 2-3% para carteira ~1,66M.
    result = calc().calculate(
        irpf=IRPFAnalyzer([_smoke_decl()]),
        patrimonio=patrimonio(investimentos_titular=1_500_000.0, investimentos_conjuge=160_000.0),
        investimentos_atuais=None,
        reference_date=date(2025, 9, 1),
        despesa_mensal_media_brl=Decimal("15000"),
    )
    assert result.status == "ok"
    assert result.renda_passiva_anual_brl == Decimal("38000.00")
    assert Decimal("2.0") < result.trs_efetiva_pct < Decimal("3.0")
    assert Decimal("3100") < result.renda_passiva_mensal_brl < Decimal("3200")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
