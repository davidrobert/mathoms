"""Pydantic schemas for the 5 editable configs: members, categories, pipeline, institutions, report_layout."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Family Members
# =============================================================================

class BankAccountSchema(BaseModel):
    """A bank account linked to a family member."""
    id: Optional[str] = None
    institution_code: str = Field(..., min_length=1, max_length=50)
    account_type: str = Field(..., min_length=1, max_length=100)
    agency: Optional[str] = Field(None, max_length=20)
    account_number: Optional[str] = Field(None, max_length=30)
    label: Optional[str] = Field(None, max_length=255)

    model_config = {"from_attributes": True}


class BankAccountCreateRequest(BaseModel):
    institution_code: str = Field(..., min_length=1, max_length=50)
    account_type: str = Field(..., min_length=1, max_length=100)
    agency: Optional[str] = Field(None, max_length=20)
    account_number: Optional[str] = Field(None, max_length=30)
    label: Optional[str] = Field(None, max_length=255)


class FamilyMemberSchema(BaseModel):
    """A family member with optional bank accounts."""
    id: Optional[str] = None
    key: str = Field(..., min_length=1, max_length=50, description="Canonical short key (e.g. 'david', 'mariana')")
    full_name: str = Field(..., min_length=1, max_length=255)
    short_name: str = Field(..., min_length=1, max_length=100)
    birth_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Nome civil anterior / de nascimento (contas antigas); persiste em extra.nome_nascimento",
    )
    cpf: Optional[str] = Field(None, max_length=14, description="CPF (masked on read, plain on write)")
    birth_date: Optional[date] = None
    role: str = Field(..., pattern=r"^(titular|conjuge|filho|dependente)$")
    order: int = Field(default=0, ge=0)
    extra: Optional[dict[str, Any]] = Field(
        None,
        description="Arbitrary extra fields (variantes_nome, regex_nome_fatura, profissao, etc.)",
    )
    accounts: list[BankAccountSchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @field_validator("cpf")
    @classmethod
    def validate_cpf_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) != 11:
            raise ValueError("CPF deve conter exatamente 11 dígitos")
        return v


class FamilyMemberCreateRequest(BaseModel):
    key: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Opcional; se omitido, gerado a partir do nome completo (slug único)",
    )
    full_name: str = Field(..., min_length=1, max_length=255)
    short_name: str = Field(..., min_length=1, max_length=100)
    birth_name: Optional[str] = Field(None, max_length=255)
    cpf: Optional[str] = Field(None, max_length=14)
    birth_date: Optional[date] = None
    role: str = Field(..., pattern=r"^(titular|conjuge|filho|dependente)$")
    order: int = Field(default=0, ge=0)
    extra: Optional[dict[str, Any]] = None

    @field_validator("key")
    @classmethod
    def normalize_optional_key(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if not s:
            return None

        if not re.fullmatch(r"[a-z0-9_]{1,50}", s):
            raise ValueError(
                "Identificador interno: use apenas letras minúsculas, números e _ (máx. 50 caracteres)"
            )
        return s

    @field_validator("cpf")
    @classmethod
    def validate_cpf_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) != 11:
            raise ValueError("CPF deve conter exatamente 11 dígitos")
        return v


class FamilyMemberUpdateRequest(BaseModel):
    key: Optional[str] = Field(None, min_length=1, max_length=50)
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    short_name: Optional[str] = Field(None, min_length=1, max_length=100)
    birth_name: Optional[str] = Field(None, max_length=255)
    cpf: Optional[str] = Field(None, max_length=14)
    birth_date: Optional[date] = None
    role: Optional[str] = Field(None, pattern=r"^(titular|conjuge|filho|dependente)$")
    order: Optional[int] = Field(None, ge=0)
    extra: Optional[dict[str, Any]] = None

    @field_validator("key")
    @classmethod
    def normalize_key(cls, v: str | None) -> str | None:
        if v is None:
            return None

        if not re.fullmatch(r"[a-z0-9_]{1,50}", v):
            raise ValueError(
                "Identificador interno: use apenas letras minúsculas, números e _ (máx. 50 caracteres)"
            )
        return v

    @field_validator("cpf")
    @classmethod
    def validate_cpf_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) != 11:
            raise ValueError("CPF deve conter exatamente 11 dígitos")
        return v


# =============================================================================
# Categories (expense_keywords + income_keywords)
# =============================================================================

class CategorySchema(BaseModel):
    """A categorization category with its keywords."""
    id: Optional[str] = None
    code: str = Field(..., min_length=1, max_length=50, description="Unique code (e.g. 'moradia', 'receita_pj')")
    name: str = Field(..., min_length=1, max_length=100)
    category_type: str = Field(..., pattern=r"^(expense|income)$")
    monthly_cap: Optional[float] = Field(None, ge=0, description="Monthly spending cap for budgeting alerts")
    order: int = Field(default=0, ge=0)
    keywords: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CategoryCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    category_type: str = Field(..., pattern=r"^(expense|income)$")
    monthly_cap: Optional[float] = Field(None, ge=0)
    order: int = Field(default=0, ge=0)
    keywords: list[str] = Field(default_factory=list)


class CategoryUpdateRequest(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category_type: Optional[str] = Field(None, pattern=r"^(expense|income)$")
    monthly_cap: Optional[float] = Field(None, ge=0)
    order: Optional[int] = Field(None, ge=0)
    keywords: Optional[list[str]] = None


# =============================================================================
# Pipeline Config (JSON blob — tolerances, thresholds, formatting)
# =============================================================================

class ReconciliationTolerancesSchema(BaseModel):
    saldo_diff: float = Field(default=0.01, ge=0)
    temporal_gap_days: int = Field(default=2, ge=0)
    baseline_irpf_diff: float = Field(default=1.0, ge=0)


class QAThresholdsSchema(BaseModel):
    score_diff_max: float = Field(default=0.5, ge=0)
    patrimonio_composicao_diff_pct_max: float = Field(default=5, ge=0)
    cv_fluxo_diff_max: float = Field(default=100, ge=0)
    cv_taxa_poupanca_diff_pp_max: float = Field(default=5, ge=0)
    cv_if_monthly_diff_max: float = Field(default=500, ge=0)
    cv_if_progress_diff_pct_max: float = Field(default=2, ge=0)
    cv_endividamento_diff_pct_max: float = Field(default=1, ge=0)
    cv_reserva_cobertura_diff_max: float = Field(default=1, ge=0)
    qa_unidentified_target_pct: float = Field(default=10.0, ge=0, le=100)


class LLMConfigSchema(BaseModel):
    model: str = Field(default="claude-sonnet-4-20250514", min_length=1)
    max_tokens: int = Field(default=500, ge=1, le=200000)
    confidence_threshold: float = Field(default=0.7, ge=0, le=1)


class FileLimitsSchema(BaseModel):
    preview_max_chars: int = Field(default=2000, ge=100)
    preview_max_rows: int = Field(default=20, ge=1)
    min_pdf_bytes: int = Field(default=1024, ge=0)
    min_xls_bytes: int = Field(default=40000, ge=0)
    min_csv_bytes: int = Field(default=500, ge=0)


class PipelineConfigSchema(BaseModel):
    """Full pipeline.json configuration — validated as a structured blob."""
    llm: Optional[LLMConfigSchema] = None
    file_limits: Optional[FileLimitsSchema] = None
    reconciliation: Optional[dict[str, Any]] = None
    qa_thresholds: Optional[QAThresholdsSchema] = None
    artifact_names: Optional[dict[str, str]] = None
    log_files: Optional[dict[str, Any]] = None
    period_regex: Optional[dict[str, str]] = None

    model_config = {"from_attributes": True}


class PipelineConfigUpdateRequest(BaseModel):
    """Partial update — only provided fields are merged."""
    llm: Optional[LLMConfigSchema] = None
    file_limits: Optional[FileLimitsSchema] = None
    reconciliation: Optional[dict[str, Any]] = None
    qa_thresholds: Optional[QAThresholdsSchema] = None
    artifact_names: Optional[dict[str, str]] = None
    log_files: Optional[dict[str, Any]] = None
    period_regex: Optional[dict[str, str]] = None


# =============================================================================
# Institution Config (JSON blob — patterns, layouts, cartoes)
# =============================================================================

class InstitutionConfigSchema(BaseModel):
    """Full institutions.json — stored as JSON blob due to deep/variable structure."""
    config_json: dict[str, Any]

    model_config = {"from_attributes": True}


class InstitutionConfigUpdateRequest(BaseModel):
    config_json: dict[str, Any]


# =============================================================================
# Report Layout (YAML→JSON blob — sections, cards, charts toggles)
# =============================================================================

class ReportLayoutSchema(BaseModel):
    """Full report_layout.yaml content — stored as JSON blob."""
    config_json: dict[str, Any]

    model_config = {"from_attributes": True}


class ReportLayoutUpdateRequest(BaseModel):
    config_json: dict[str, Any]


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


# =============================================================================
# List wrappers
# =============================================================================

class FamilyMemberListResponse(BaseModel):
    members: list[FamilyMemberSchema]
    total: int


class CategoryListResponse(BaseModel):
    categories: list[CategorySchema]
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
