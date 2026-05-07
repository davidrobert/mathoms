"""Invariantes das constantes metodológicas (ADR-177).

Estes testes garantem que os valores migrados de ``goals.json`` em A10.2
não foram alterados sem revisão. Mudar qualquer um exige PR explícito
(gate intencional do rules-as-code).
"""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.methodology_constants import (
    APORTE_REDUZIDO_FATOR_CONJUGE,
    EQUITY_PCT_ALVO_DEFAULT_MAX,
    EQUITY_PCT_ALVO_DEFAULT_MIN,
    IMOVEL_PCT_PATRIMONIO_IDEAL,
    STRESS_TEST_IMOVEL_QUEDA_PCT,
    YIELD_POTENCIAL_FII_BR_PCT_MAX,
    YIELD_POTENCIAL_FII_BR_PCT_MIN,
)


def test_yield_potencial_fii_br_pct_range_4_to_6() -> None:
    assert YIELD_POTENCIAL_FII_BR_PCT_MIN == Decimal("4.0")
    assert YIELD_POTENCIAL_FII_BR_PCT_MAX == Decimal("6.0")
    assert YIELD_POTENCIAL_FII_BR_PCT_MIN < YIELD_POTENCIAL_FII_BR_PCT_MAX


def test_imovel_pct_patrimonio_ideal_is_50() -> None:
    assert IMOVEL_PCT_PATRIMONIO_IDEAL == Decimal("50")


def test_equity_pct_alvo_default_range_20_to_25() -> None:
    assert EQUITY_PCT_ALVO_DEFAULT_MIN == Decimal("20")
    assert EQUITY_PCT_ALVO_DEFAULT_MAX == Decimal("25")
    assert EQUITY_PCT_ALVO_DEFAULT_MIN < EQUITY_PCT_ALVO_DEFAULT_MAX


def test_aporte_reduzido_fator_conjuge_is_0_66() -> None:
    """Convergente Cerbasi (renda dupla, ADR-167)."""
    assert APORTE_REDUZIDO_FATOR_CONJUGE == Decimal("0.66")


def test_stress_test_imovel_queda_pct_is_20() -> None:
    assert STRESS_TEST_IMOVEL_QUEDA_PCT == Decimal("20")
