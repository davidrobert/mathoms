"""Pydantic schemas for the 5 editable configs: members, categories, pipeline, institutions, report_layout.

**A6e (ADR-101)** — os DTOs dos agregados ``FamilyMember`` / ``BankAccount``
(A6e.1+.2), ``Category`` / ``CategoryKeyword`` (A6e.3) e dos 3 blobs de
config ``Pipeline``/``Institution``/``ReportLayout`` (A6e.4) migraram para
``backend.app.schemas.dto.{agregado}``. Os nomes legados aqui são
**aliases** durante a janela de transição (tests e imports antigos
continuam funcionando). Use os DTOs novos em código novo.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

# A6e aliases (preservam nomes legados apontando para os DTOs canônicos).
from backend.app.schemas.dto.category.command import (
    CategoryCreateCommand as CategoryCreateRequest,
    CategoryUpdateCommand as CategoryUpdateRequest,
)
from backend.app.schemas.dto.category.response import (
    CategoryListResponse as _CategoryListResponse,
    CategoryResponse as CategorySchema,
)
from backend.app.schemas.dto.config_blob.command import (
    InstitutionConfigUpdateCommand as InstitutionConfigUpdateRequest,
    PipelineConfigUpdateCommand as PipelineConfigUpdateRequest,
    ReportLayoutUpdateCommand as ReportLayoutUpdateRequest,
)
from backend.app.schemas.dto.config_blob.response import (
    FileLimitsSchema as _FileLimitsSchema,
    InstitutionConfigResponse as InstitutionConfigSchema,
    LLMConfigSchema as _LLMConfigSchema,
    PipelineConfigResponse as PipelineConfigSchema,
    QAThresholdsSchema as _QAThresholdsSchema,
    ReconciliationTolerancesSchema as _ReconciliationTolerancesSchema,
    ReportLayoutResponse as ReportLayoutSchema,
)
from backend.app.schemas.dto.family_member.command import (
    BankAccountCreateCommand as BankAccountCreateRequest,
    FamilyMemberCreateCommand as FamilyMemberCreateRequest,
    FamilyMemberUpdateCommand as FamilyMemberUpdateRequest,
)
from backend.app.schemas.dto.family_member.response import (
    BankAccountResponse as BankAccountSchema,
    FamilyMemberListResponse as _FamilyMemberListResponse,
    FamilyMemberResponse as FamilyMemberSchema,
)

# Aliases legados — mantêm os nomes servindo o mesmo shape dos DTOs novos.
FamilyMemberListResponse = _FamilyMemberListResponse
CategoryListResponse = _CategoryListResponse

# Sub-schemas tipados do Pipeline também re-exportados sem underscore, para
# manter imports legados (`from backend.app.schemas.config import LLMConfigSchema`)
# funcionando durante a janela A6e.
FileLimitsSchema = _FileLimitsSchema
LLMConfigSchema = _LLMConfigSchema
QAThresholdsSchema = _QAThresholdsSchema
ReconciliationTolerancesSchema = _ReconciliationTolerancesSchema


# =============================================================================
# Import / Export
# =============================================================================

class ConfigImportRequest(BaseModel):
    """Import config from JSON (pipeline CLI format). Only provided keys are imported."""
    family_members: Optional[dict[str, Any]] = None
    categorization: Optional[dict[str, Any]] = None
    pipeline: Optional[dict[str, Any]] = None
    institutions: Optional[dict[str, Any]] = None
    report_layout: Optional[dict[str, Any]] = None


class ConfigExportResponse(BaseModel):
    """Export all configs for the workspace (DB values + defaults for unedited)."""
    family_members: dict[str, Any]
    categorization: dict[str, Any]
    pipeline: dict[str, Any]
    institutions: dict[str, Any]
    report_layout: dict[str, Any]


class ConfigImportResponse(BaseModel):
    """Retorno de ``POST /config/import`` — reporta quais seções foram importadas."""
    imported: list[str]
    total: int


# =============================================================================
# Workspace settings (family_surname etc.)
# =============================================================================

class WorkspaceSettingsSchema(BaseModel):
    """Workspace-level settings consumed by the report (E6 cover, filename)."""
    name: str = Field(..., description="Internal workspace name")
    family_surname: Optional[str] = Field(
        None,
        max_length=255,
        description="Sobrenome da família — aparece como {{COVER_FAMILIA}} no relatório E6 e no nome do arquivo HTML.",
    )

    model_config = {"from_attributes": True}


class WorkspaceSettingsUpdateRequest(BaseModel):
    """Partial update for workspace settings. Use null to clear family_surname."""
    family_surname: Optional[str] = Field(None, max_length=255)
