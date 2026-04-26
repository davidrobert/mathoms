"""``ConfigStore`` — protocolo de leitura tipado para configs do pipeline (ADR-134)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional, Protocol, runtime_checkable

from pipeline.domain.types.config import (
    CategorizationConfig,
    FamilyMembersConfig,
    FiscalParameters,
    InstitutionsCatalog,
    ReportLayout,
    TransferConfig,
)


@runtime_checkable
class ConfigStore(Protocol):
    """Boundary única para leitura de configs do pipeline (ADR-134)."""

    def get_categorization(self, workspace_id: str) -> Optional[CategorizationConfig]:
        """Categorização do workspace ou ``None`` se não há row."""
        ...

    def get_family_members(self, workspace_id: str) -> Optional[FamilyMembersConfig]:
        """Membros + bank_to_member + transferências do workspace ou ``None``."""
        ...

    def get_institutions(self) -> InstitutionsCatalog:
        """Catálogo global de instituições — mesmo para todos workspaces."""
        ...

    def get_report_layout(self, workspace_id: str) -> Optional[ReportLayout]:
        """Layout de relatório do workspace ou ``None``."""
        ...

    def get_transfer_config(self, workspace_id: str) -> Optional[TransferConfig]:
        """Config de transferências internas (ADR-133) do workspace ou ``None``."""
        ...

    def get_fiscal_for_period(self, period_start: date, period_end: date) -> FiscalParameters:
        """Parâmetros fiscais vigentes em ``[period_start, period_end]`` (A7.2b)."""
        ...

    def get_market_rate(self, pair: str, observed_at: date) -> Decimal:
        """Última cotação de ``pair`` em ``observed_at`` ou antes (A7.2b)."""
        ...
