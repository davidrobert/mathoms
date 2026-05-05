"""Tests — ``PassiveIncomeCalculator`` core (Lane A8.3 PR-A): buckets + status."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer
from pipeline.domain.services.passive_income_calculator import (
    PassiveIncomeConfig,
    PassiveIncomeResult,
)
from pipeline.llm.schemas.e16_irpf_full import (
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
)
from tests.unit.pipeline._passive_income_builders import (
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
        assert result.renda_passiva_por_fonte_brl["ganho_capital"] == Decimal("20000.00")

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
            result.patrimonio_gerador_brl,
            result.trs_efetiva_pct,
            result.acumuladores_pct_gerador,
        ):
            assert isinstance(v, Decimal)
        for value in result.renda_passiva_por_fonte_brl.values():
            assert isinstance(value, Decimal)

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
