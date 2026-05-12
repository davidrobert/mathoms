"""Calculator ``life_insurance_coverage_ideal`` (ADR-192 §D3, S9-T03) — cobertura ideal = ``max(Cerbasi, Perini)``. Cerbasi: 10× renda anual × fator deps (1.0/1.5/2.0). Perini: PV anuidade até maioridade do dep mais novo, taxa real 3% default. Boundary ADR-101 R5; cents int64 (ADR-090)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from pipeline.domain.protection_bundle import RiskInferred
from pipeline.domain.services.protection.disclaimer import render_disclaimer
from pipeline.domain.services.protection.risk_inferred import build_risk_inferred

# Cerbasi: fator multiplicativo aplicado ao baseline ``10 × renda_anual_ativa``
# em função do nº de dependentes em minoridade. Fonte: "Equilíbrio Financeiro"
# §"Proteção da Renda" — proteção cresce com responsabilidade familiar.
_CERBASI_BASE_MULTIPLE: Decimal = Decimal("10")
_CERBASI_DEPENDENCY_FACTORS: dict[int, Decimal] = {
    0: Decimal("1.0"),
    1: Decimal("1.5"),
    2: Decimal("1.5"),
    3: Decimal("2.0"),  # 3+ dependentes minoridade
}

# Perini: taxa real default de desconto do fluxo de renda durante a minoridade
# do dependente mais novo. 3% a.a. é conservador para BR pós-juros reais
# históricos. Pode ser sobrescrito pelo adapter via ``inputs.discount_rate_pct``.
_DEFAULT_DISCOUNT_RATE_PCT: Decimal = Decimal("3.0")

# Idade limiar de "minoridade" para fins do cálculo Perini.
_MINORIDADE_LIMITE_ANOS: int = 18


@dataclass(frozen=True)
class LifeInsuranceInputs:
    """Inputs tipados para ``life_insurance_coverage_ideal`` (ADR-097 D2/D3); cents int64 (ADR-090)."""

    principal_age: int
    dependents_ages: tuple[int, ...]
    annual_active_income_brl_cents: int
    outstanding_debts_brl_cents: int
    current_coverage_brl_cents: int
    effective_date: str  # ISO 8601 — propagado para o disclaimer
    discount_rate_pct: Decimal = field(default=_DEFAULT_DISCOUNT_RATE_PCT)


@dataclass(frozen=True)
class CoverageRecommendation:
    """Output do calculator de cobertura ideal de vida."""

    ideal_brl_cents: int
    actual_brl_cents: int
    gap_brl_cents: int
    methodology: str  # "max" — default; "cerbasi" / "perini" se forçado
    cerbasi_ideal_brl_cents: int
    perini_ideal_brl_cents: int
    rationale: str
    risk_inferred: Optional[RiskInferred] = None


def _dependency_factor(n_minors: int) -> Decimal:
    """Cerbasi: fator multiplicativo por quantidade de dependentes minoridade."""
    if n_minors <= 0:
        return _CERBASI_DEPENDENCY_FACTORS[0]
    if n_minors >= 3:
        return _CERBASI_DEPENDENCY_FACTORS[3]
    return _CERBASI_DEPENDENCY_FACTORS[n_minors]


def _cerbasi_ideal(
    annual_active_income_brl_cents: int, n_minors: int, outstanding_debts_brl_cents: int
) -> int:
    """``10 × renda_anual × fator_deps + dívidas`` (ADR-192 §D3 / Cerbasi)."""
    if annual_active_income_brl_cents <= 0:
        return max(0, outstanding_debts_brl_cents)
    base = Decimal(annual_active_income_brl_cents) * _CERBASI_BASE_MULTIPLE
    factor = _dependency_factor(n_minors)
    coverage = base * factor + Decimal(outstanding_debts_brl_cents)
    return int(coverage.to_integral_value())


def _pv_factor_anuidade(years: int, rate_pct: Decimal) -> Decimal:
    """PV anuidade ordinária: ``(1 - (1+i)^-n) / i`` · i = rate_pct/100."""
    rate = rate_pct / Decimal("100")
    if rate <= 0:
        return Decimal(years)
    return (Decimal("1") - (Decimal("1") + rate) ** Decimal(-years)) / rate


def _perini_ideal(
    annual_active_income_brl_cents: int,
    dependents_ages: tuple[int, ...],
    outstanding_debts_brl_cents: int,
    discount_rate_pct: Decimal,
) -> int:
    """PV de renda anual × anos restantes de minoridade (Perini); sem deps → só dívidas."""
    minors = [a for a in dependents_ages if 0 <= a < _MINORIDADE_LIMITE_ANOS]
    if not minors or annual_active_income_brl_cents <= 0:
        return max(0, outstanding_debts_brl_cents)
    years_remaining = _MINORIDADE_LIMITE_ANOS - min(minors)
    if years_remaining <= 0:
        return max(0, outstanding_debts_brl_cents)
    pv = Decimal(annual_active_income_brl_cents) * _pv_factor_anuidade(
        years_remaining, discount_rate_pct
    )
    return int((pv + Decimal(outstanding_debts_brl_cents)).to_integral_value())


def _count_minors(dependents_ages: tuple[int, ...]) -> int:
    return sum(1 for age in dependents_ages if 0 <= age < _MINORIDADE_LIMITE_ANOS)


def _format_brl(cents: int) -> str:
    """``2_500_000_00`` → ``'R$ 2.500.000'`` (sem centavos, formato copy)."""
    reais = cents // 100
    return f"R$ {reais:_.0f}".replace("_", ".")


def _is_material_gap(gap: int, ideal: int) -> bool:
    """Gap material: > 5% do ideal E > R$ 50k absoluto. Evita ruído de arredondamento."""
    if ideal <= 0 or gap <= 0:
        return False
    return (Decimal(gap) / Decimal(ideal)) > Decimal("0.05") and gap > 50_000_00


def _life_rationale(ideal: int, cerbasi: int, perini: int, actual: int, gap: int, dl: str) -> str:
    return (
        f"Cobertura ideal estimada em {_format_brl(ideal)} "
        f"(Cerbasi: {_format_brl(cerbasi)}; Perini: {_format_brl(perini)}; "
        f"adotado o maior por conservadorismo). "
        f"Cobertura atual: {_format_brl(actual)}; gap: {_format_brl(gap)}. {dl}"
    )


def _compute_ideals(inputs: LifeInsuranceInputs) -> tuple[int, int]:
    """Retorna ``(cerbasi_ideal, perini_ideal)`` em cents."""
    n_minors = _count_minors(inputs.dependents_ages)
    cerbasi = _cerbasi_ideal(
        inputs.annual_active_income_brl_cents, n_minors, inputs.outstanding_debts_brl_cents
    )
    perini = _perini_ideal(
        inputs.annual_active_income_brl_cents,
        inputs.dependents_ages,
        inputs.outstanding_debts_brl_cents,
        inputs.discount_rate_pct,
    )
    return cerbasi, perini


def _life_risk(gap: int, ideal: int, rationale: str):
    if not _is_material_gap(gap, ideal):
        return None
    return build_risk_inferred(
        category="vida",
        name="falta_seguro_vida_cobertura_insuficiente",
        rationale=rationale,
        estimated_impact_brl_cents=gap,
        source_calculator="life_insurance_coverage_ideal",
    )


def _build_life_recommendation(
    cerbasi: int, perini: int, actual: int, effective_date: str
) -> CoverageRecommendation:
    ideal = max(cerbasi, perini)
    gap = max(0, ideal - actual)
    disclaimer = render_disclaimer(
        sources="Cerbasi (10× renda) e Perini (PV minoridade)",
        effective_date=effective_date,
    )
    rationale = _life_rationale(ideal, cerbasi, perini, actual, gap, disclaimer)
    return CoverageRecommendation(
        ideal_brl_cents=ideal,
        actual_brl_cents=actual,
        gap_brl_cents=gap,
        methodology="max",
        cerbasi_ideal_brl_cents=cerbasi,
        perini_ideal_brl_cents=perini,
        rationale=rationale,
        risk_inferred=_life_risk(gap, ideal, rationale),
    )


def life_insurance_coverage_ideal(inputs: LifeInsuranceInputs) -> CoverageRecommendation:
    """Cobertura ideal de vida = ``max(Cerbasi, Perini)`` (ADR-192 §D3); puro, idempotente."""
    cerbasi, perini = _compute_ideals(inputs)
    actual = max(0, inputs.current_coverage_brl_cents)
    return _build_life_recommendation(cerbasi, perini, actual, inputs.effective_date)


__all__ = [
    "CoverageRecommendation",
    "LifeInsuranceInputs",
    "life_insurance_coverage_ideal",
]
