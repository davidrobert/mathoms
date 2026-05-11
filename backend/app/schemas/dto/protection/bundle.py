"""Bundle DTOs Pydantic (ADR-192) — espelha `pipeline.domain.protection_bundle`."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProtectionItemResponse(BaseModel):
    """Apólice agregada no bundle (subset do `ProtectionResponse`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    category: str
    holder_family_member_id: Optional[str] = None
    insurer: Optional[str] = None
    coverage_brl: Decimal
    premium_monthly_brl: Optional[Decimal] = None
    coverage_type: Optional[str] = None
    starts_at: date
    ends_at: Optional[date] = None
    status: str


class ProtectionGapItemResponse(BaseModel):
    """Gap por categoria (T03 popula via calculators)."""

    model_config = ConfigDict(extra="forbid")

    ideal_brl: Optional[Decimal] = None
    actual_brl: Decimal
    gap_brl: Optional[Decimal] = None
    methodology: Optional[str] = None


class ProtectionRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    rationale: str
    priority: str


class RiskInferredResponse(BaseModel):
    """Risco inferido por calculator (T03 popula)."""

    model_config = ConfigDict(extra="forbid")

    category: str
    name: str
    rationale: str
    estimated_impact_brl: Optional[Decimal] = None
    source_calculator: str


class ProtectionThresholdsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    life_insurance_multiple_renda_anual: Optional[float] = None
    reserva_meses_clt: Optional[int] = None
    reserva_meses_pj: Optional[int] = None
    reserva_meses_socio_variavel: Optional[int] = None
    fbar_threshold_usd: Optional[int] = None
    estate_tax_threshold_usd: Optional[int] = None


class ProtectionBundleResponse(BaseModel):
    """Bundle exposto via ``GET /workspaces/{id}/protection-bundle``."""

    model_config = ConfigDict(extra="forbid")

    policies: list[ProtectionItemResponse]
    gap_analysis: dict[str, ProtectionGapItemResponse]
    recommendations: list[ProtectionRecommendationResponse]
    auto_inferred_risks: list[RiskInferredResponse]
    methodology_thresholds: ProtectionThresholdsResponse
    has_us_exposure: bool
    adapter_version: int
