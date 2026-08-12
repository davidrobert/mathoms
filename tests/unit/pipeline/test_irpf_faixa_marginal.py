"""Tests — `resolve_faixa_marginal` (ADR-375 D6)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.irpf_faixa_marginal import (  # noqa: E402
    TabelaProgressivaInvalida,
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
