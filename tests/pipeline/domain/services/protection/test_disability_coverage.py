"""Testes ``disability_coverage_gap`` (ADR-192 §D3, S9-T03)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.protection.disability_coverage import (
    DisabilityInputs,
    disability_coverage_gap,
)
from pipeline.domain.services.protection.risk_inferred import SOURCE_CALCULATORS_WHITELIST

_EFFECTIVE_DATE = "2026-05-12"


def _inputs(**overrides) -> DisabilityInputs:
    defaults = dict(
        active_net_monthly_income_brl_cents=0,
        passive_net_monthly_income_brl_cents=0,
        current_disability_coverage_monthly_brl_cents=0,
        effective_date=_EFFECTIVE_DATE,
        target_pct=Decimal("0.60"),
    )
    defaults.update(overrides)
    return DisabilityInputs(**defaults)


def test_solteiro_clt_sem_invalidez_emite_risk() -> None:
    """Renda 100% ativa, cobertura zero → Cerbasi dispara (share=100% > 40%, gap >0)."""
    # Renda líquida mensal R$ 10k.
    gap = disability_coverage_gap(_inputs(active_net_monthly_income_brl_cents=10_000_00))
    assert gap.active_income_share == Decimal("1")  # 100% ativa
    # Target = 60% × 10k = R$ 6k.
    assert gap.gap_brl_cents_mensal == 6_000_00
    assert gap.risk_inferred is not None
    assert gap.risk_inferred["source_calculator"] == "disability_coverage_gap"
    assert gap.risk_inferred["source_calculator"] in SOURCE_CALCULATORS_WHITELIST
    # Impacto anualizado.
    assert gap.risk_inferred["estimated_impact_brl_cents"] == 6_000_00 * 12


def test_casado_com_renda_passiva_majoritaria_nao_emite() -> None:
    """Renda passiva > 60% → share ativa < 40% → não dispara (capital cobre risco)."""
    gap = disability_coverage_gap(
        _inputs(
            active_net_monthly_income_brl_cents=2_000_00,  # R$ 2k
            passive_net_monthly_income_brl_cents=10_000_00,  # R$ 10k
        )
    )
    # Share ≈ 2/12 ≈ 16.7%.
    assert gap.active_income_share < Decimal("0.40")
    # Gap pode existir, mas trigger não dispara.
    assert gap.risk_inferred is None


def test_expatriado_freelance_com_cobertura_parcial() -> None:
    """Renda 100% ativa, cobertura 50% da renda → gap = (60%-50%)×renda."""
    gap = disability_coverage_gap(
        _inputs(
            active_net_monthly_income_brl_cents=20_000_00,
            current_disability_coverage_monthly_brl_cents=10_000_00,  # 50%
        )
    )
    # Target = 60% × 20k = 12k. Gap = 12k - 10k = R$ 2k/mês.
    assert gap.gap_brl_cents_mensal == 2_000_00
    assert gap.risk_inferred is not None


def test_share_ativa_no_limite_40pct_nao_dispara() -> None:
    """Cerbasi: gate é ``share > 40%``, não ``>=`` — exatamente 40% não dispara."""
    # Ativa = 4k, passiva = 6k → share = 40% (não >).
    gap = disability_coverage_gap(
        _inputs(
            active_net_monthly_income_brl_cents=4_000_00,
            passive_net_monthly_income_brl_cents=6_000_00,
        )
    )
    assert gap.active_income_share == Decimal("0.4")
    assert gap.risk_inferred is None


def test_workspace_vazio_sem_renda_share_zero() -> None:
    """Total=0: share=0; risk_inferred=None."""
    gap = disability_coverage_gap(_inputs())
    assert gap.active_income_share == Decimal("0")
    assert gap.gap_brl_cents_mensal == 0
    assert gap.risk_inferred is None


def test_disclaimer_presente_no_rationale() -> None:
    gap = disability_coverage_gap(_inputs(active_net_monthly_income_brl_cents=10_000_00))
    assert "não constitui recomendação fiduciária" in gap.rationale
    assert "Susep" in gap.rationale
    assert _EFFECTIVE_DATE in gap.rationale


def test_idempotente() -> None:
    inputs = _inputs(active_net_monthly_income_brl_cents=10_000_00)
    g1 = disability_coverage_gap(inputs)
    g2 = disability_coverage_gap(inputs)
    assert g1 == g2


def test_gap_imaterial_nao_emite() -> None:
    """Gap < R$ 1k/mês não emite risco (ruído)."""
    # Target 60% × 1500 cents = 900 cents (~R$9), cob = 800 cents, gap = 100 cents.
    gap = disability_coverage_gap(
        _inputs(
            active_net_monthly_income_brl_cents=1500,
            current_disability_coverage_monthly_brl_cents=800,
        )
    )
    assert gap.gap_brl_cents_mensal > 0
    assert gap.risk_inferred is None  # imaterial


def test_cobertura_acima_do_target_zera_gap() -> None:
    """Cobertura > 60% renda → gap = 0; sem risk."""
    gap = disability_coverage_gap(
        _inputs(
            active_net_monthly_income_brl_cents=10_000_00,
            current_disability_coverage_monthly_brl_cents=20_000_00,
        )
    )
    assert gap.gap_brl_cents_mensal == 0
    assert gap.risk_inferred is None
