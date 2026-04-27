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
from pipeline.domain.types.snapshot_changelog import (
    AnalyzeFinancesSnapshot,
    ChangelogEntry,
    ComparisonItem,
    ComparisonResult,
    DeltaSignal,
    SnapshotChangelogConfig,
    UnknownSectionError,
)

__all__ = [
    "AnalyzeFinancesSnapshot",
    "CategorizationConfig",
    "CategoryDef",
    "ChangelogEntry",
    "ComparisonItem",
    "ComparisonResult",
    "DeltaSignal",
    "FamilyMemberRecord",
    "FamilyMembersConfig",
    "FiscalParameters",
    "InstitutionDef",
    "InstitutionsCatalog",
    "IRPFBracket",
    "MarketRate",
    "ReportLayout",
    "SnapshotChangelogConfig",
    "TransferConfig",
    "TransferInternalConfig",
    "UnknownSectionError",
]
