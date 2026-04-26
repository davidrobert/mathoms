"""``InMemoryConfigStore`` — fake nomeado para testes de domínio (ADR-134)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pipeline.domain.types.config import (
    CategorizationConfig,
    FamilyMembersConfig,
    FiscalParameters,
    InstitutionsCatalog,
    MarketRate,
    ReportLayout,
    TransferConfig,
)


class InMemoryConfigStore:
    """Implementação em-memória do ``ConfigStore`` — usar em testes (ADR-134 R15)."""

    def __init__(
        self,
        *,
        categorization: Optional[CategorizationConfig] = None,
        family_members: Optional[FamilyMembersConfig] = None,
        institutions: Optional[InstitutionsCatalog] = None,
        report_layout: Optional[ReportLayout] = None,
        transfer_config: Optional[TransferConfig] = None,
        fiscal_by_year: Optional[dict[int, FiscalParameters]] = None,
        market_rates: Optional[dict[tuple[str, date], Decimal]] = None,
    ) -> None:
        self._categorization = categorization
        self._family_members = family_members
        self._institutions = institutions or InstitutionsCatalog(institutions={})
        self._report_layout = report_layout
        self._transfer_config = transfer_config
        self._fiscal_by_year = fiscal_by_year or {}
        self._market_rates = market_rates or {}

    def get_categorization(self, workspace_id: str) -> Optional[CategorizationConfig]:
        del workspace_id
        return self._categorization

    def get_family_members(self, workspace_id: str) -> Optional[FamilyMembersConfig]:
        del workspace_id
        return self._family_members

    def get_institutions(self) -> InstitutionsCatalog:
        return self._institutions

    def get_report_layout(self, workspace_id: str) -> Optional[ReportLayout]:
        del workspace_id
        return self._report_layout

    def get_transfer_config(self, workspace_id: str) -> Optional[TransferConfig]:
        del workspace_id
        return self._transfer_config

    def get_fiscal_for_period(self, period_start: date, period_end: date) -> FiscalParameters:
        """Retorna a row cujo ano coincide com ``period_start.year`` ou raise."""
        params = self._fiscal_by_year.get(period_start.year)
        if params is None:
            raise KeyError(f"InMemoryConfigStore: no fiscal params for year={period_start.year}")
        del period_end
        return params

    def get_market_rate(self, pair: str, observed_at: date) -> Decimal:
        """Retorna a cotação exata ou raise ``KeyError`` (testes pedem matches exatos)."""
        rate = self._market_rates.get((pair, observed_at))
        if rate is None:
            raise KeyError(
                f"InMemoryConfigStore: no market rate for pair={pair!r} on {observed_at.isoformat()}"
            )
        return rate
