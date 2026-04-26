"""Tipos cross-cutting do domínio do pipeline (ex.: retornos de ``ConfigStore`` — ADR-134)."""

from pipeline.domain.types.config import (
    CategorizationConfig,
    CategoryDef,
    FamilyMemberRecord,
    FamilyMembersConfig,
    FiscalParameters,
    InstitutionDef,
    InstitutionsCatalog,
    IRPFBracket,
    MarketRate,
    ReportLayout,
    TransferConfig,
    TransferInternalConfig,
)

__all__ = [
    "CategorizationConfig",
    "CategoryDef",
    "FamilyMemberRecord",
    "FamilyMembersConfig",
    "FiscalParameters",
    "InstitutionDef",
    "InstitutionsCatalog",
    "IRPFBracket",
    "MarketRate",
    "ReportLayout",
    "TransferConfig",
    "TransferInternalConfig",
]
