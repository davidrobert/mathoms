"""Calculator ``disability_coverage_gap`` (ADR-192 §D3, S9-T03) — Cerbasi: dispara quando renda ativa > 40% da total **e** cobertura mensal < 60% da renda ativa líquida (família dependente de capital humano). Boundary ADR-101 R5: stdlib + ``pipeline.domain.*`` apenas; cents int64 (ADR-090)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from pipeline.domain.protection_bundle import RiskInferred
from pipeline.domain.services.protection.disclaimer import render_disclaimer
from pipeline.domain.services.protection.risk_inferred import build_risk_inferred

# Cerbasi: percentual mínimo de cobertura de invalidez sobre renda ativa
# líquida mensal. Default 60% — coincide com despesa essencial típica do
# perfil Mathoms.
_DEFAULT_TARGET_PCT: Decimal = Decimal("0.60")

# Cerbasi: limite mínimo da participação de renda ativa para o gap ser
# relevante (abaixo disto, renda passiva já cobre risco de invalidez).
_ACTIVE_INCOME_DEPENDENCY_THRESHOLD: Decimal = Decimal("0.40")


@dataclass(frozen=True)
class DisabilityInputs:
    """Inputs tipados para ``disability_coverage_gap`` (ADR-097 D2/D3); cents mensais (ADR-090)."""

    active_net_monthly_income_brl_cents: int
    passive_net_monthly_income_brl_cents: int
    current_disability_coverage_monthly_brl_cents: int
    effective_date: str
    target_pct: Decimal = field(default=_DEFAULT_TARGET_PCT)


@dataclass(frozen=True)
class CoverageGap:
    """Output do calculator de gap de invalidez."""

    gap_brl_cents_mensal: int
    target_pct: Decimal
    active_income_share: Decimal  # fração de renda ativa / renda total (0-1)
    rationale: str
    risk_inferred: Optional[RiskInferred] = None


def _format_brl_monthly(cents: int) -> str:
    reais = cents // 100
    return f"R$ {reais:_.0f}/mês".replace("_", ".")


def _active_share(active: int, passive: int) -> Decimal:
    total = active + passive
    return Decimal(active) / Decimal(total) if total > 0 else Decimal("0")


def _disability_rationale(
    share: Decimal, target_cov: int, actual_cov: int, gap: int, disclaimer: str
) -> str:
    share_pct = (share * Decimal("100")).quantize(Decimal("0.1"))
    return (
        f"Renda ativa = {share_pct}% da renda total mensal; "
        f"cobertura-alvo (60% da renda ativa líquida): {_format_brl_monthly(target_cov)}; "
        f"cobertura atual: {_format_brl_monthly(actual_cov)}; "
        f"gap: {_format_brl_monthly(gap)}. {disclaimer}"
    )


def _disability_risk(gap: int, share: Decimal, rationale: str):
    """Cerbasi: dispara se share > 40% E gap > R$ 1k/mês (material). Senão None."""
    if share <= _ACTIVE_INCOME_DEPENDENCY_THRESHOLD or gap <= 1_000_00:
        return None
    return build_risk_inferred(
        category="invalidez",
        name="invalidez_subcobertura",
        rationale=rationale,
        estimated_impact_brl_cents=gap * 12,
        source_calculator="disability_coverage_gap",
    )


def disability_coverage_gap(inputs: DisabilityInputs) -> CoverageGap:
    """Gap mensal de invalidez (Cerbasi · ADR-192 §D3); puro, idempotente (ADR-111)."""
    active = max(0, inputs.active_net_monthly_income_brl_cents)
    passive = max(0, inputs.passive_net_monthly_income_brl_cents)
    actual_cov = max(0, inputs.current_disability_coverage_monthly_brl_cents)
    share = _active_share(active, passive)
    target_coverage = int((Decimal(active) * inputs.target_pct).to_integral_value())
    gap = max(0, target_coverage - actual_cov)
    disclaimer = render_disclaimer(
        sources="Cerbasi (renda ativa dominante → 60% mínimo)",
        effective_date=inputs.effective_date,
    )
    rationale = _disability_rationale(share, target_coverage, actual_cov, gap, disclaimer)
    return CoverageGap(
        gap_brl_cents_mensal=gap,
        target_pct=inputs.target_pct,
        active_income_share=share,
        rationale=rationale,
        risk_inferred=_disability_risk(gap, share, rationale),
    )


__all__ = ["CoverageGap", "DisabilityInputs", "disability_coverage_gap"]
