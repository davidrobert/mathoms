"""Inputs observados para cálculos do ``ProtectionBundle`` (A40.l61)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from pipeline.domain.services.protection import USPersonThresholds
from pipeline.domain.services.protection.compliance_us_person import USTaxStatus


@dataclass(frozen=True)
class ProtectionComputationInputs:
    """Valores ausentes permanecem ``None`` e retêm o calculator correspondente."""

    annual_active_income_brl_cents: int | None = None
    outstanding_debts_brl_cents: int | None = None
    active_net_monthly_income_brl_cents: int | None = None
    passive_net_monthly_income_brl_cents: int | None = None
    gross_estate_brl_cents: int | None = None
    itcmd_uf: str | None = None
    itcmd_aliquota_pct_por_uf: Mapping[str, Decimal] | None = None
    has_us_assets: bool | None = None
    has_us_income: bool | None = None
    us_tax_status: USTaxStatus | None = None
    us_assets_usd: int | None = None
    us_thresholds: USPersonThresholds | None = None


__all__ = ["ProtectionComputationInputs"]
