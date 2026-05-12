"""Testes ``life_insurance_coverage_ideal`` (ADR-192 §D3, S9-T03) — valores em cents int64 (ADR-090): R$1=100 / R$1k=100_000 / R$120k=12_000_000 / R$1.2M=120_000_000."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.protection.life_insurance_coverage import (
    LifeInsuranceInputs,
    life_insurance_coverage_ideal,
)
from pipeline.domain.services.protection.risk_inferred import SOURCE_CALCULATORS_WHITELIST

_EFFECTIVE_DATE = "2026-05-12"

# Atalhos de unidade: BRL → cents.
_R = 100  # 1 real = 100 cents
_K = 1_000 * _R  # mil reais
_M = 1_000_000 * _R  # milhão de reais


def _inputs(**overrides) -> LifeInsuranceInputs:
    defaults = dict(
        principal_age=40,
        dependents_ages=(),
        annual_active_income_brl_cents=0,
        outstanding_debts_brl_cents=0,
        current_coverage_brl_cents=0,
        effective_date=_EFFECTIVE_DATE,
        discount_rate_pct=Decimal("3.0"),
    )
    defaults.update(overrides)
    return LifeInsuranceInputs(**defaults)


def test_solteiro_sem_renda_sem_dependentes_zera_tudo() -> None:
    """Workspace vazio: ideal=0, actual=0, gap=0, sem risk_inferred."""
    rec = life_insurance_coverage_ideal(_inputs())
    assert rec.ideal_brl_cents == 0
    assert rec.actual_brl_cents == 0
    assert rec.gap_brl_cents == 0
    assert rec.risk_inferred is None
    assert "Estimativa metodológica" in rec.rationale  # disclaimer presente


def test_solteiro_com_renda_sem_dependentes() -> None:
    """Cerbasi base (10× renda) sem fator de dependência. Perini cai p/ dívidas (0)."""
    rec = life_insurance_coverage_ideal(
        _inputs(annual_active_income_brl_cents=120 * _K)  # R$ 120k anuais
    )
    # Cerbasi: 10 × 120k = R$ 1.2M.
    assert rec.cerbasi_ideal_brl_cents == 1_200 * _K
    # Perini: sem deps minoridade → 0.
    assert rec.perini_ideal_brl_cents == 0
    assert rec.ideal_brl_cents == 1_200 * _K  # max
    assert rec.methodology == "max"
    assert rec.gap_brl_cents == 1_200 * _K
    # Material → emite RiskInferred.
    assert rec.risk_inferred is not None
    assert rec.risk_inferred["source_calculator"] == "life_insurance_coverage_ideal"
    assert rec.risk_inferred["source_calculator"] in SOURCE_CALCULATORS_WHITELIST


def test_casado_com_2_deps_minoridade_max_perini_ou_cerbasi() -> None:
    """Família com 2 deps em minoridade. Fator dependência = 1.5. Perini ativo."""
    rec = life_insurance_coverage_ideal(
        _inputs(
            principal_age=38,
            dependents_ages=(8, 12),
            annual_active_income_brl_cents=240 * _K,  # R$ 240k anuais
            outstanding_debts_brl_cents=500 * _K,  # R$ 500k dívidas
        )
    )
    # Cerbasi: 10 × 240k × 1.5 + 500k = R$ 3.6M + R$ 500k = R$ 4.1M.
    assert rec.cerbasi_ideal_brl_cents == 4_100 * _K
    # Perini: PV anuidade 240k por 10 anos (18-8=10) a 3% real + 500k.
    # PV factor (10y, 3%) ≈ 8.5302 → PV ≈ 240k × 8.5302 + 500k ≈ R$ 2.55M.
    assert 2_000 * _K < rec.perini_ideal_brl_cents < 3_000 * _K
    assert rec.ideal_brl_cents == max(rec.cerbasi_ideal_brl_cents, rec.perini_ideal_brl_cents)
    assert rec.methodology == "max"
    assert rec.risk_inferred is not None
    assert rec.risk_inferred["category"] == "vida"


def test_expatriado_usa_com_dependente_jovem_perini_proximo_cerbasi() -> None:
    """Dependente recém-nascido → Perini cobre 18 anos."""
    rec = life_insurance_coverage_ideal(
        _inputs(
            principal_age=33,
            dependents_ages=(0,),
            annual_active_income_brl_cents=60 * _K,  # R$ 60k anuais
            outstanding_debts_brl_cents=0,
        )
    )
    # Cerbasi: 10 × 60k × 1.5 = R$ 900k.
    assert rec.cerbasi_ideal_brl_cents == 900 * _K
    # Perini: PV 60k por 18 anos a 3% real factor ≈ 13.7535 → ~R$ 825k.
    assert 800 * _K < rec.perini_ideal_brl_cents < 850 * _K
    assert rec.ideal_brl_cents == max(rec.cerbasi_ideal_brl_cents, rec.perini_ideal_brl_cents)


def test_gap_zero_quando_cobertura_excede_ideal_nao_emite_risk() -> None:
    """Cliente over-segurado: gap=0, sem risk_inferred."""
    rec = life_insurance_coverage_ideal(
        _inputs(
            annual_active_income_brl_cents=120 * _K,  # ideal Cerbasi ~ 1.2M
            current_coverage_brl_cents=2 * _M,  # R$ 2M, > ideal
        )
    )
    assert rec.gap_brl_cents == 0
    assert rec.risk_inferred is None


def test_gap_imaterial_nao_emite_risk_inferred() -> None:
    """Gap < 5% do ideal E < R$ 50k → não emite."""
    # Renda R$ 10k anuais → Cerbasi = R$ 100k = 10_000_000 cents.
    # Cobertura R$ 99k → gap = R$ 1k = 100_000 cents (< R$ 50k absoluto).
    rec = life_insurance_coverage_ideal(
        _inputs(
            annual_active_income_brl_cents=10 * _K,
            current_coverage_brl_cents=99 * _K,
        )
    )
    assert rec.gap_brl_cents > 0
    assert rec.risk_inferred is None  # gap imaterial


def test_disclaimer_canonical_text_presente() -> None:
    """ADR-192: disclaimer obrigatório em todo rationale."""
    rec = life_insurance_coverage_ideal(_inputs(annual_active_income_brl_cents=120 * _K))
    assert "não constitui recomendação fiduciária" in rec.rationale
    assert "Susep" in rec.rationale
    assert "CFP®" in rec.rationale
    assert _EFFECTIVE_DATE in rec.rationale


def test_idempotente_mesma_entrada_mesma_saida() -> None:
    """ADR-111: calculator puro, idempotente."""
    inputs = _inputs(annual_active_income_brl_cents=120 * _K, dependents_ages=(8, 12))
    rec1 = life_insurance_coverage_ideal(inputs)
    rec2 = life_insurance_coverage_ideal(inputs)
    assert rec1 == rec2


def test_3_ou_mais_deps_minoridade_fator_2x() -> None:
    """Fator dependência salta para 2.0 com 3+ deps minoridade."""
    rec = life_insurance_coverage_ideal(
        _inputs(
            annual_active_income_brl_cents=120 * _K,
            dependents_ages=(5, 10, 15, 17),
        )
    )
    # Cerbasi: 10 × 120k × 2.0 = R$ 2.4M.
    assert rec.cerbasi_ideal_brl_cents == 2_400 * _K


def test_dependentes_maioridade_nao_contam_em_fator() -> None:
    """Deps >= 18 não entram no fator Cerbasi nem influenciam Perini."""
    rec = life_insurance_coverage_ideal(
        _inputs(
            annual_active_income_brl_cents=120 * _K,
            dependents_ages=(18, 20, 22),
        )
    )
    # Fator = 1.0 (zero minoridades).
    assert rec.cerbasi_ideal_brl_cents == 1_200 * _K
    # Perini: sem minoridade → 0.
    assert rec.perini_ideal_brl_cents == 0


@pytest.mark.parametrize("renda_anual_cents", [0, -1, -100 * _K])
def test_renda_invalida_zera_cerbasi_mas_mantem_dividas(renda_anual_cents: int) -> None:
    """Renda ≤0: Cerbasi colapsa para dívidas; calculator não explode."""
    rec = life_insurance_coverage_ideal(
        _inputs(
            annual_active_income_brl_cents=renda_anual_cents,
            outstanding_debts_brl_cents=100 * _K,
        )
    )
    assert rec.cerbasi_ideal_brl_cents == 100 * _K
