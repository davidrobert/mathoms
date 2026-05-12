"""Whitelist ``source_calculator`` para ``RiskInferred`` (ADR-192 §D3) — instrumentos jurídicos (holding/D&O/fideicomisso) ficam fora pois exigem análise fiduciária habilitada."""

from __future__ import annotations

from typing import Optional

# Importa o TypedDict para o helper de construção emitir shape correto.
from pipeline.domain.protection_bundle import RiskInferred

SOURCE_CALCULATORS_WHITELIST: frozenset[str] = frozenset(
    {
        "life_insurance_coverage_ideal",
        "disability_coverage_gap",
        "itcmd_estimated",
        "compliance_risk_us_person",
    }
)


def _assert_whitelisted(source_calculator: str) -> None:
    if source_calculator not in SOURCE_CALCULATORS_WHITELIST:
        raise ValueError(
            f"source_calculator inválido: {source_calculator!r}. "
            f"Lista branca: {sorted(SOURCE_CALCULATORS_WHITELIST)}"
        )


def build_risk_inferred(
    *,
    category: str,
    name: str,
    rationale: str,
    source_calculator: str,
    estimated_impact_brl_cents: Optional[int] = None,
) -> RiskInferred:
    """``RiskInferred`` validado vs whitelist; ``ValueError`` se ``source_calculator`` fora."""
    _assert_whitelisted(source_calculator)
    return {
        "category": category,
        "name": name,
        "rationale": rationale,
        "estimated_impact_brl_cents": estimated_impact_brl_cents,
        "source_calculator": source_calculator,
    }


__all__ = ["SOURCE_CALCULATORS_WHITELIST", "build_risk_inferred"]
