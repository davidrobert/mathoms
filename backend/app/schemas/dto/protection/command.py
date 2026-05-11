"""Command DTOs do aggregate `Protection` (ADR-192). Money wire = decimal BRL (ADR-090)."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.protection import (
    VALID_PROTECTION_CATEGORIES,
    VALID_PROTECTION_COVERAGE_TYPES,
    VALID_PROTECTION_STATUSES,
)

# Allowlist regex para ``insurer`` (sre-devops review): letras (com
# acentos PT-BR), dígitos, espaço e separadores comuns (incl. ``/`` para
# ``S/A``); bloqueia URL/path para defesa de SSRF — sem ``:``, ``//``,
# ``\``, ``<>``, ``http``. Validador adicional rejeita ``//``.
_INSURER_ALLOWED = re.compile(r"^[A-Za-zÀ-ÿ0-9 .&,'\-/]{1,120}$")


class ProtectionCreateCommand(BaseModel):
    """Cria nova apólice (status default = ``Ativa``)."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(..., min_length=1, max_length=32)
    holder_family_member_id: Optional[str] = Field(None, min_length=36, max_length=36)
    insurer: Optional[str] = Field(None, max_length=120)
    policy_ref: Optional[str] = Field(None, max_length=200)
    coverage_brl: Decimal = Field(..., description="Capital segurado em BRL (string decimal).")
    premium_monthly_brl: Optional[Decimal] = None
    coverage_type: Optional[str] = None
    starts_at: date
    ends_at: Optional[date] = None
    status: str = "Ativa"
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v: str) -> str:
        if v not in VALID_PROTECTION_CATEGORIES:
            raise ValueError(
                f"category inválida: {v!r}; aceitas: {sorted(VALID_PROTECTION_CATEGORIES)}"
            )
        return v

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        if v not in VALID_PROTECTION_STATUSES:
            raise ValueError(
                f"status inválido: {v!r}; aceitos: {sorted(VALID_PROTECTION_STATUSES)}"
            )
        return v

    @field_validator("coverage_type")
    @classmethod
    def _validate_coverage_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_PROTECTION_COVERAGE_TYPES:
            raise ValueError(
                f"coverage_type inválido: {v!r}; aceitos: {sorted(VALID_PROTECTION_COVERAGE_TYPES)}"
            )
        return v

    @field_validator("insurer")
    @classmethod
    def _validate_insurer(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            return None
        if "//" in stripped or "\\" in stripped:
            raise ValueError("insurer contém separadores de URL/path proibidos")
        if not _INSURER_ALLOWED.match(stripped):
            raise ValueError(
                "insurer contém caracteres não permitidos; aceitos: letras, dígitos, espaço, .,&'/-"
            )
        return stripped


class ProtectionUpdateCommand(BaseModel):
    """Patch parcial dos campos editoriais."""

    model_config = ConfigDict(extra="forbid")

    holder_family_member_id: Optional[str] = Field(None, min_length=36, max_length=36)
    insurer: Optional[str] = Field(None, max_length=120)
    policy_ref: Optional[str] = Field(None, max_length=200)
    coverage_brl: Optional[Decimal] = None
    premium_monthly_brl: Optional[Decimal] = None
    coverage_type: Optional[str] = None
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("coverage_type")
    @classmethod
    def _validate_coverage_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_PROTECTION_COVERAGE_TYPES:
            raise ValueError(
                f"coverage_type inválido: {v!r}; aceitos: {sorted(VALID_PROTECTION_COVERAGE_TYPES)}"
            )
        return v

    @field_validator("insurer")
    @classmethod
    def _validate_insurer(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            return None
        if "//" in stripped or "\\" in stripped:
            raise ValueError("insurer contém separadores de URL/path proibidos")
        if not _INSURER_ALLOWED.match(stripped):
            raise ValueError(
                "insurer contém caracteres não permitidos; aceitos: letras, dígitos, espaço, .,&'/-"
            )
        return stripped


class ProtectionCancelCommand(BaseModel):
    """Cancela uma apólice (soft delete via ``status='Cancelada'``)."""

    model_config = ConfigDict(extra="forbid")

    reason: Optional[str] = Field(None, max_length=500)


class ProtectionLinkToRiskCommand(BaseModel):
    """Vincula apólice como mitigação de um Risk (ADR-192 §D1)."""

    model_config = ConfigDict(extra="forbid")

    risk_id: str = Field(..., min_length=36, max_length=36)
