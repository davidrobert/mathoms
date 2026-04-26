"""``DBConfigStore`` — adapter SQLAlchemy do ``ConfigStore`` (ADR-134)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.services.config_materializer import (
    serialize_categorization,
    serialize_family_members,
    serialize_institution_config,
    serialize_report_layout,
    serialize_transfer_config,
)
from pipeline.adapters.config_parsers import (
    parse_categorization,
    parse_family_members,
    parse_institutions,
    parse_report_layout,
    parse_transfers,
)
from pipeline.domain.types.config import (
    CategorizationConfig,
    FamilyMembersConfig,
    FiscalParameters,
    InstitutionsCatalog,
    ReportLayout,
    TransferConfig,
)


class DBConfigStore:
    """Lê configs do banco via ``serialize_*`` + parsers compartilhados."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_categorization(self, workspace_id: str) -> Optional[CategorizationConfig]:
        """``categories`` + ``category_keywords`` rows do workspace."""
        data = serialize_categorization(workspace_id, self._session)
        if not data:
            return None
        return parse_categorization(data)

    def get_family_members(self, workspace_id: str) -> Optional[FamilyMembersConfig]:
        """``family_members`` + ``bank_accounts`` + ``transfer_configs`` do workspace."""
        data = serialize_family_members(workspace_id, self._session)
        if not data:
            return None
        merged = _merge_transfer_block(data, workspace_id, self._session)
        return parse_family_members(merged)

    def get_institutions(self) -> InstitutionsCatalog:
        """Catálogo global — não é workspace-scoped no DB hoje (ADR-137 split em A7.3)."""
        # A7.0 ainda lê o blob do primeiro workspace que tenha config customizada,
        # com fallback para empty. A7.3 introduz ``institution_catalog`` global.
        return InstitutionsCatalog(institutions={})

    def get_report_layout(self, workspace_id: str) -> Optional[ReportLayout]:
        """``report_layouts`` row do workspace ou ``None``."""
        data = serialize_report_layout(workspace_id, self._session)
        if not data:
            return None
        return parse_report_layout(data)

    def get_transfer_config(self, workspace_id: str) -> Optional[TransferConfig]:
        """``transfer_configs`` row do workspace (ADR-133) ou ``None``."""
        data = serialize_transfer_config(workspace_id, self._session)
        if not data:
            return None
        return TransferConfig(config=parse_transfers(data))

    def get_institutions_for_workspace(self, workspace_id: str) -> InstitutionsCatalog:
        """Custom institution config do workspace ou catálogo global vazio."""
        data = serialize_institution_config(workspace_id, self._session)
        if not data:
            return InstitutionsCatalog(institutions={})
        return parse_institutions(data)

    def get_fiscal_for_period(self, period_start: date, period_end: date) -> FiscalParameters:
        """Stub A7.2b — tabela ``fiscal_parameters`` é seedada em A7.2b (ADR-135)."""
        del period_start, period_end
        raise NotImplementedError("get_fiscal_for_period is populated in Sprint A7.2b (ADR-135).")

    def get_market_rate(self, pair: str, observed_at: date) -> Decimal:
        """Stub A7.2b — tabela ``market_rates`` é seedada em A7.2b (ADR-135)."""
        del pair, observed_at
        raise NotImplementedError("get_market_rate is populated in Sprint A7.2b (ADR-135).")


def _merge_transfer_block(
    family_data: dict[str, Any], workspace_id: str, session: Session
) -> dict[str, Any]:
    """Funde ``transferencias_internas`` (ADR-133) ao blob de family_members se houver row."""
    transfer_data = serialize_transfer_config(workspace_id, session)
    if not transfer_data:
        return family_data
    merged = dict(family_data)
    merged["transferencias_internas"] = transfer_data
    return merged
