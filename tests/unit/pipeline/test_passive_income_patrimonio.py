"""Tests — ``PassiveIncomeCalculator`` patrimônio gerador + acumuladores (A8.3 PR-A)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer
from pipeline.domain.services.passive_income_calculator import PassiveIncomeConfig
from pipeline.llm.schemas.e16_irpf_full import CodigoRendimentoIsento
from tests.unit.pipeline._passive_income_builders import (
    calc,
    decl,
    holdings,
    isento,
    patrimonio,
)

_REF_DATE = date(2025, 6, 1)
_NO_DESPESA = Decimal("0")


def _decl_basico():
    return decl(isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "10000.00")])


# ---------------------------------------------------------------------------
# Patrimonio gerador — exclusões (D1 metodologia)
# ---------------------------------------------------------------------------


class TestPatrimonioGeradorExclusoes:
    def test_residencia_e_veiculos_excluidos(self):
        result = calc().calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(
                investimentos_titular=500_000.0,
                residencia=2_000_000.0,
                veiculos=150_000.0,
            ),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.patrimonio_gerador_brl == Decimal("500000.0")

    def test_imoveis_investimento_incluso_default(self):
        result = calc().calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=300_000.0, imoveis_investimento=400_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.patrimonio_gerador_brl == Decimal("700000.0")

    def test_imoveis_investimento_excluido_via_config(self):
        cfg = PassiveIncomeConfig(incluir_imoveis_investimento=False)
        result = calc(cfg).calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=300_000.0, imoveis_investimento=400_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.patrimonio_gerador_brl == Decimal("300000.0")

    def test_caixa_excedente_acima_da_reserva_entra(self):
        # despesa 5k/mês * 6m = reserva 30k. Caixa 80k → excedente 50k.
        result = calc().calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=100_000.0, caixa=80_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=Decimal("5000"),
        )
        assert result.patrimonio_gerador_brl == Decimal("150000.0")

    def test_caixa_abaixo_da_reserva_nao_entra(self):
        result = calc().calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=100_000.0, caixa=20_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=Decimal("5000"),
        )
        assert result.patrimonio_gerador_brl == Decimal("100000.0")

    def test_caixa_le_alias_legado_em_artefato_e5_antigo(self):
        """CTO-08 (A37.l15): produtor não emite mais o alias, mas artefatos E5
        antigos re-lidos sem re-run trazem só `caixa_moeda_estrangeira` — o
        fallback de leitura deve seguir funcionando."""
        patrimonio_legado = patrimonio(investimentos_titular=100_000.0)
        del patrimonio_legado["caixa_total_brl"]
        patrimonio_legado["caixa_moeda_estrangeira"] = 80_000.0
        result = calc().calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio_legado,
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=Decimal("5000"),
        )
        # reserva 30k (5k × 6m) → excedente 50k entra no gerador.
        assert result.patrimonio_gerador_brl == Decimal("150000.0")

    def test_derivativos_subtraidos_via_patrimonio_field(self):
        result = calc().calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=500_000.0, derivativos=80_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.patrimonio_gerador_brl == Decimal("420000.0")

    def test_derivativos_subtraidos_via_holdings_tipo(self):
        h = holdings(
            [
                {"nome": "PUT IBOV", "tipo": "derivativo", "valor_atual": 25_000.0},
                {"nome": "BOVA11", "tipo": "etf", "valor_atual": 50_000.0},
            ]
        )
        result = calc().calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=300_000.0),
            investimentos_atuais=h,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        # 300k - 25k derivativo
        assert result.patrimonio_gerador_brl == Decimal("275000.0")


# ---------------------------------------------------------------------------
# Acumuladores — heurística para banner UI
# ---------------------------------------------------------------------------


class TestAcumuladores:
    def test_zero_acumuladores_quando_holdings_diversificadas(self):
        h = holdings([{"nome": "ITUB4", "tipo": "acao", "valor_atual": 200_000.0}])
        result = calc().calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=200_000.0),
            investimentos_atuais=h,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.acumuladores_pct_gerador == Decimal("0")

    def test_25_pct_acumuladores(self):
        h = holdings(
            [
                {"nome": "BOVA11", "tipo": "etf", "valor_atual": 100_000.0},
                {"nome": "ITUB4", "tipo": "acao", "valor_atual": 300_000.0},
            ]
        )
        result = calc().calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=400_000.0),
            investimentos_atuais=h,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        # 100k acumulador / 400k gerador = 25%
        assert result.acumuladores_pct_gerador == Decimal("25.00")

    def test_60_pct_dispara_banner_threshold(self):
        h = holdings(
            [
                {"nome": "IVVB11", "tipo": "etf", "valor_atual": 600_000.0},
                {"nome": "PETR4", "tipo": "acao", "valor_atual": 400_000.0},
            ]
        )
        result = calc().calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=1_000_000.0),
            investimentos_atuais=h,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.acumuladores_pct_gerador == Decimal("60.00")


# ---------------------------------------------------------------------------
# PGBL em acumulação — yield 0% explícito (D1 metodologia)
# ---------------------------------------------------------------------------


def test_pgbl_em_acumulacao_entra_no_gerador_com_yield_zero():
    # PGBL não rende dividendos hoje, mas conta como carteira de renda — exclui-lo
    # mascararia concentração (D1). Status ``ok``; renda zero → trs 0,00%.
    d = decl()
    h = holdings([{"nome": "PGBL ITAU FLEXPREV", "tipo": "previdencia", "valor_atual": 200_000.0}])
    result = calc().calculate(
        irpf=IRPFAnalyzer([d]),
        patrimonio=patrimonio(investimentos_titular=200_000.0),
        investimentos_atuais=h,
        reference_date=_REF_DATE,
        despesa_mensal_media_brl=_NO_DESPESA,
    )
    assert result.status == "ok"
    assert result.patrimonio_gerador_brl == Decimal("200000.0")
    assert result.renda_passiva_anual_brl == Decimal("0")
    assert result.trs_efetiva_pct == Decimal("0.00")


# ---------------------------------------------------------------------------
# Defasagem
# ---------------------------------------------------------------------------


class TestDefasagem:
    def test_defasagem_natural_4_meses(self):
        # Ano-base 2024 declarado em ~abril/2025; em 2025-05 defasagem ~ 4m.
        d = decl(
            ano_base=2024,
            isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "1000.00")],
        )
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(investimentos_titular=100_000.0),
            investimentos_atuais=None,
            reference_date=date(2025, 5, 1),
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.defasagem_meses == 4

    def test_defasagem_grande_aciona_banner(self):
        # Ano-base 2023 + reference 2025-09 → 20 meses (≥15 = warning).
        d = decl(
            ano_base=2023,
            isentos=[isento(CodigoRendimentoIsento.lucros_dividendos, "1000.00")],
        )
        result = calc().calculate(
            irpf=IRPFAnalyzer([d]),
            patrimonio=patrimonio(investimentos_titular=100_000.0),
            investimentos_atuais=None,
            reference_date=date(2025, 9, 1),
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.defasagem_meses == 20


# ---------------------------------------------------------------------------
# Config overrides
# ---------------------------------------------------------------------------


class TestConfigOverrides:
    def test_reserva_emergencia_custom_meses(self):
        cfg = PassiveIncomeConfig(reserva_emergencia_meses=12)
        # despesa 5k * 12m = 60k reserva alvo. Caixa 70k → excedente 10k.
        result = calc(cfg).calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=100_000.0, caixa=70_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=Decimal("5000"),
        )
        assert result.patrimonio_gerador_brl == Decimal("110000.0")

    def test_excluir_derivativos_off_mantem_derivativos(self):
        cfg = PassiveIncomeConfig(excluir_derivativos=False)
        result = calc(cfg).calculate(
            irpf=IRPFAnalyzer([_decl_basico()]),
            patrimonio=patrimonio(investimentos_titular=500_000.0, derivativos=80_000.0),
            investimentos_atuais=None,
            reference_date=_REF_DATE,
            despesa_mensal_media_brl=_NO_DESPESA,
        )
        assert result.patrimonio_gerador_brl == Decimal("500000.0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
