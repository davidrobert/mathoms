"""Tests — `resolve_faixa_marginal` (ADR-375 D6) + `ir_devido_anual` (D5)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.irpf_faixa_marginal import (  # noqa: E402
    TabelaProgressivaInvalida,
    ir_devido_anual,
    resolve_faixa_marginal,
)
from pipeline.domain.types.config import IRPFBracket  # noqa: E402


def _faixa(upper: int | None, pct: str) -> IRPFBracket:
    return IRPFBracket(upper_brl_cents=upper, aliquota_pct=Decimal(pct), deducao_brl_cents=0)


#: Seed real de `fiscal_parameters` (migration y3z4a5b6c7d8, anos 2024-2026).
SEEDADAS = (
    _faixa(2696320, "0.0"),
    _faixa(3391980, "7.5"),
    _faixa(4501260, "15.0"),
    _faixa(5597616, "22.5"),
    _faixa(None, "27.5"),
)


@pytest.mark.parametrize(
    "cents,esperado",
    [
        (0, "0.0"),
        (1_152_000, "0.0"),
        (2_696_320, "0.0"),
        (2_696_321, "7.5"),
        (3_391_980, "7.5"),
        (3_391_981, "15.0"),
        (4_501_260, "15.0"),
        (4_501_261, "22.5"),
        (5_597_616, "22.5"),
        (5_597_617, "27.5"),
        (115_200_000, "27.5"),
    ],
)
def test_teto_inclusivo_em_cada_fronteira(cents, esperado):
    """`upper_brl_cents` é teto INCLUSIVO: renda igual ao teto fica na faixa."""
    assert resolve_faixa_marginal(cents, SEEDADAS) == Decimal(esperado)


def test_tabela_vazia_recusa():
    """Resolver faixa sem faixas é erro do chamador; a política de degradação é dele."""
    with pytest.raises(TabelaProgressivaInvalida, match="vazia"):
        resolve_faixa_marginal(1_000_000, ())


def test_sem_terminal_e_acima_do_topo_recusa():
    """Comportamento antes indefinido: o loop devolvia a faixa excedida, por acidente."""
    sem_terminal = (_faixa(2_400_000, "7.5"), _faixa(4_800_000, "15.0"))
    with pytest.raises(TabelaProgressivaInvalida, match="não tem faixa terminal"):
        resolve_faixa_marginal(10_000_000, sem_terminal)


def test_sem_terminal_mas_dentro_do_topo_resolve():
    """A recusa é só para o que a tabela não cobre — dentro dela, resolve normalmente."""
    sem_terminal = (_faixa(2_400_000, "7.5"), _faixa(4_800_000, "15.0"))
    assert resolve_faixa_marginal(3_000_000, sem_terminal) == Decimal("15.0")


def test_faixa_de_teto_zero_nao_vira_terminal():
    """Regressão do falsy-zero: teto 0 cobre só a base 0, não toda renda."""
    com_zero = (_faixa(0, "0.0"), _faixa(None, "27.5"))
    assert resolve_faixa_marginal(0, com_zero) == Decimal("0.0")
    assert resolve_faixa_marginal(1, com_zero) == Decimal("27.5")


# =============================================================================
# ADR-375 D5 — `ir_devido_anual`: a tabela aplicada, não só a faixa resolvida
# =============================================================================


# Derivada da MIGRATION, nunca de literais aqui: `SEEDADAS` acima zera as parcelas
# a deduzir por conveniência, e é justamente a parcela que o D5 usa. Uma cópia à
# mão diverge em centavos (medido: 472991 vs 472992) e o teste passa a medir a
# fantasia em vez da tabela que roda.
def _anual_da_seed(ano: int = 2026) -> tuple[IRPFBracket, ...]:
    from datetime import date

    from tests.pipeline_golden_substrate import fiscal_store_do_seed

    fiscal = fiscal_store_do_seed(ano).get_fiscal_for_period(date(ano, 1, 1), date(ano, 12, 31))
    return fiscal.ir_brackets_anual.faixas


ANUAL_2026 = _anual_da_seed()


class TestIRDevidoAnual:
    @pytest.mark.parametrize(
        "base_reais,esperado_reais",
        [
            ("20000", "0"),  # faixa isenta
            ("60000", "5595.34"),  # terminal: 60000 × 27,5% − 10.904,66
            ("50000", "3144.15"),  # 22,5%: 50000 × 22,5% − 8.105,85
            ("30000", "64.08"),  # 7,5%: 30000 × 7,5% − 2.185,92
        ],
    )
    def test_aplica_aliquota_menos_parcela_a_deduzir(self, base_reais, esperado_reais):
        cents = ir_devido_anual(int(Decimal(base_reais) * 100), ANUAL_2026)
        assert Decimal(cents) / 100 == Decimal(esperado_reais)

    def test_nunca_negativo(self):
        """Base no piso da faixa: a parcela a deduzir excede o imposto bruto."""
        assert ir_devido_anual(2914561, ANUAL_2026) >= 0

    def test_tabela_vazia_recusa(self):
        """Mesma política de `resolve_faixa_marginal`: sem faixas é defeito de config."""
        with pytest.raises(TabelaProgressivaInvalida):
            ir_devido_anual(6_000_000, ())

    def test_progressividade_e_monotonica(self):
        """Renda maior nunca paga menos — falsifica troca de faixa mal ordenada."""
        devidos = [ir_devido_anual(b, ANUAL_2026) for b in range(0, 12_000_000, 250_000)]
        assert devidos == sorted(devidos)
