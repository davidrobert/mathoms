"""Whitelist de ``source_calculator`` para ``RiskInferred`` (ADR-192 §D3, S9-T03)."""

from __future__ import annotations

import pytest

from pipeline.domain.services.protection.risk_inferred import (
    SOURCE_CALCULATORS_WHITELIST,
    build_risk_inferred,
)


def test_whitelist_contem_exatamente_4_calculators() -> None:
    """ADR-192 §D3 explicita: 4 calculators, não 5 nem outros."""
    assert SOURCE_CALCULATORS_WHITELIST == frozenset(
        {
            "life_insurance_coverage_ideal",
            "disability_coverage_gap",
            "itcmd_estimated",
            "compliance_risk_us_person",
        }
    )


@pytest.mark.parametrize("calc", sorted(SOURCE_CALCULATORS_WHITELIST))
def test_build_aceita_calculator_whitelisted(calc: str) -> None:
    risk = build_risk_inferred(
        category="vida",
        name="x",
        rationale="r",
        source_calculator=calc,
    )
    assert risk["source_calculator"] == calc


def test_build_rejeita_calculator_fora_da_whitelist() -> None:
    with pytest.raises(ValueError, match="source_calculator inválido"):
        build_risk_inferred(
            category="vida",
            name="x",
            rationale="r",
            source_calculator="holding_familiar_estrategia",  # instrumento jurídico
        )


def test_build_rejeita_emergency_reserve_target() -> None:
    """ADR-192 §"Atualizações": emergency_reserve_target MOVIDO para Goal (ADR-180)."""
    with pytest.raises(ValueError, match="source_calculator inválido"):
        build_risk_inferred(
            category="reserva",
            name="x",
            rationale="r",
            source_calculator="emergency_reserve_target",
        )
