"""``DBConfigStore`` — adapter SQLAlchemy do ``ConfigStore`` (ADR-134)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.repositories.fiscal_parameter_repository import (
    FiscalParameterRepository,
)
from backend.app.repositories.market_rate_repository import MarketRateRepository
from backend.app.services import fiscal_cache
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
from pipeline.adapters.fiscal_parsers import (
    fiscal_payload_to_dataclass,
    fiscal_row_to_payload,
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
        """Resolver template global + overrides do workspace (A7.3 · ADR-137)."""
        from backend.app.services.category_resolver import (
            METADATA_TEMPLATE_KEY,
            resolve_categories,
        )
        from pipeline.domain.types.config import CategoryDef

        try:
            resolved = resolve_categories(workspace_id, self._session)
        except Exception:
            # Fallback A7.5-window: ainda há paridade com legacy ``categories`` table.
            data = serialize_categorization(workspace_id, self._session)
            if not data:
                return None
            return parse_categorization(data)
        if not resolved:
            # Sem template seedada → fallback legado para evitar quebra.
            data = serialize_categorization(workspace_id, self._session)
            if not data:
                return None
            return parse_categorization(data)
        del METADATA_TEMPLATE_KEY  # filtrado pelo resolver
        categories = {
            c.key: CategoryDef(
                code=c.key,
                name=c.label,
                keywords=c.keywords,
                monthly_cap_cents=c.monthly_cap_brl_cents,
            )
            for c in resolved
        }
        return CategorizationConfig(categories=categories, metadata={})

    def get_family_members(self, workspace_id: str) -> Optional[FamilyMembersConfig]:
        """``family_members`` + ``bank_accounts`` + ``transfer_configs`` do workspace."""
        data = serialize_family_members(workspace_id, self._session)
        if not data:
            return None
        merged = _merge_transfer_block(data, workspace_id, self._session)
        return parse_family_members(merged)

    def get_institutions(self) -> InstitutionsCatalog:
        """Catálogo global via ``institution_catalog`` (A7.3 · ADR-137)."""
        from backend.app.services.institution_resolver import resolve_institutions

        return resolve_institutions(self._session)

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
        """Lê ``fiscal_parameters`` por vigência; raise se 0 ou ≥2 rows (ADR-135)."""
        row = FiscalParameterRepository(self._session).get_for_period(period_start, period_end)
        cached = fiscal_cache.get_cached_fiscal(row.year)
        if cached is None:
            cached = fiscal_row_to_payload(row)
            fiscal_cache.store_fiscal_cache(row.year, cached)
        return fiscal_payload_to_dataclass(cached)

    def get_market_rate(self, pair: str, observed_at: date) -> Decimal:
        """Lê última cotação de ``pair`` em data <= ``observed_at`` (ADR-135)."""
        cached = fiscal_cache.get_cached_market_rate(pair, observed_at)
        if cached is not None:
            return cached
        rate = MarketRateRepository(self._session).get_rate(pair, observed_at)
        fiscal_cache.store_market_rate_cache(pair, observed_at, rate)
        return rate

    def get_protection_bundle(self, workspace_id: str):
        """Bundle de proteção (ADR-192). Skeleton T02 — calculators T03."""
        from backend.app.services.pipeline_adapter import build_protection_bundle_sync

        return build_protection_bundle_sync(workspace_id, db=self._session)


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
