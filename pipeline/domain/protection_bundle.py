"""`ProtectionBundle` TypedDict (ADR-192) — espelha `GoalsBundle` (ADR-180)."""

from __future__ import annotations

from typing import Literal, NotRequired, Optional, TypedDict


class ProtectionItem(TypedDict):
    """Apólice projetada para consumo do pipeline e do bubble S9."""

    id: str
    category: str
    holder_family_member_id: Optional[str]
    insurer: Optional[str]
    coverage_brl_cents: int
    premium_monthly_brl_cents: Optional[int]
    coverage_type: Optional[str]
    starts_at: str  # ISO 8601 date
    ends_at: Optional[str]  # ISO 8601 date | None
    status: str
    insured_family_member_id: NotRequired[Optional[str]]
    benefit_mode: NotRequired[Optional[str]]
    benefit_monthly_brl_cents: NotRequired[Optional[int]]


class ProtectionGapItem(TypedDict, total=False):
    """Gap analysis por categoria (preenchido em T03 pelos calculators)."""

    ideal_brl_cents: Optional[int]
    actual_brl_cents: int
    gap_brl_cents: Optional[int]
    methodology: Optional[str]  # "cerbasi" | "perini" | "max"


class ProtectionRecommendation(TypedDict, total=False):
    """Recomendação textual associada a uma categoria (T03+)."""

    category: str
    rationale: str
    priority: str  # "alta" | "média" | "baixa"


class RiskInferred(TypedDict, total=False):
    """Risco inferido por calculator determinístico (T03) — não persistido."""

    category: str
    name: str
    rationale: str
    estimated_impact_brl_cents: Optional[int]
    source_calculator: str


class ProtectionThresholds(TypedDict, total=False):
    """Thresholds metodológicos (T03 popula via ``fiscal_parameters``)."""

    life_insurance_multiple_renda_anual: Optional[float]
    reserva_meses_clt: Optional[int]
    reserva_meses_pj: Optional[int]
    reserva_meses_socio_variavel: Optional[int]
    fbar_threshold_usd: Optional[int]
    estate_tax_threshold_usd: Optional[int]


class ProtectionCalculationStatus(TypedDict):
    """Computabilidade explícita; ausência de dado nunca é gap zero."""

    status: Literal["computed", "not_applicable", "missing_data"]
    missing_inputs: list[str]
    reason: str


# ADR-395 §D2 — o que o documento sustenta, sem virar valor. `insurers` e
# `earliest_coverage_end` existem para o render NOMEAR o identificado; a copy
# nunca deriva de `missing_inputs`, que carrega identificador interno.
class DocumentaryCoverage(TypedDict):
    """Fonte documental (ADR-240) projetada no bundle — hint, nunca aritmética."""

    active_policies_count: int
    insurers: list[str]
    earliest_coverage_end: Optional[str]
    unconfirmed_categories: list[str]


class ProtectionBundle(TypedDict, total=False):
    """Bundle tipado consumido por stages do pipeline (ADR-192; total=False)."""

    policies: list[ProtectionItem]
    gap_analysis: dict[str, ProtectionGapItem]  # key = category
    recommendations: list[ProtectionRecommendation]
    auto_inferred_risks: list[RiskInferred]
    calculation_status: dict[str, ProtectionCalculationStatus]
    methodology_thresholds: ProtectionThresholds
    has_us_exposure: Optional[bool]
    documentary_coverage: DocumentaryCoverage
    _adapter_version: int


__all__ = [
    "DocumentaryCoverage",
    "ProtectionBundle",
    "ProtectionCalculationStatus",
    "ProtectionGapItem",
    "ProtectionItem",
    "ProtectionRecommendation",
    "ProtectionThresholds",
    "RiskInferred",
]
