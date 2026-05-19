"""Command DTOs (inputs de write) do agregado ``FamilyMember``.

Um *command* é a representação de uma **intenção** do caller (criar,
atualizar, apagar). É validado na camada de transporte antes de chegar ao
use case.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator

_KEY_PATTERN = re.compile(r"[a-z0-9_]{1,50}")


def _validate_cpf_11_digits(v: str | None) -> str | None:
    if v is None:
        return v
    digits = "".join(c for c in v if c.isdigit())
    if len(digits) != 11:
        raise ValueError("CPF deve conter exatamente 11 dígitos")
    return v


def _validate_key_slug_optional(v: str | None) -> str | None:
    """Usado no Create: empty/whitespace → None (sinaliza auto-gen)."""
    if v is None:
        return None
    s = v.strip()
    if not s:
        return None
    if not _KEY_PATTERN.fullmatch(s):
        raise ValueError(
            "Identificador interno: use apenas letras minúsculas, números e _ "
            "(máx. 50 caracteres)"
        )
    return s


def _validate_key_slug_strict(v: str | None) -> str | None:
    """Usado no Update: string explícita deve seguir slug pattern."""
    if v is None:
        return None
    if not _KEY_PATTERN.fullmatch(v):
        raise ValueError(
            "Identificador interno: use apenas letras minúsculas, números e _ "
            "(máx. 50 caracteres)"
        )
    return v


class FamilyMemberCreateCommand(BaseModel):
    """Input do ``POST /members``."""

    key: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description=("Opcional; se omitido, backend gera slug único a partir de " "``full_name``."),
    )
    full_name: str = Field(..., min_length=1, max_length=255)
    short_name: str = Field(..., min_length=1, max_length=100)
    birth_name: Optional[str] = Field(None, max_length=255)
    cpf: Optional[str] = Field(None, max_length=14)
    birth_date: Optional[date] = None
    role: str = Field(..., pattern=r"^(titular|conjuge|filho|dependente)$")
    order: int = Field(default=0, ge=0)
    extra: Optional[dict[str, object]] = None

    @field_validator("key")
    @classmethod
    def _key(cls, v: str | None) -> str | None:
        return _validate_key_slug_optional(v)

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: str | None) -> str | None:
        return _validate_cpf_11_digits(v)


class FamilyMemberUpdateCommand(BaseModel):
    """Input do ``PUT /members/{id}`` — todos os campos opcionais (partial update)."""

    key: Optional[str] = Field(None, min_length=1, max_length=50)
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    short_name: Optional[str] = Field(None, min_length=1, max_length=100)
    birth_name: Optional[str] = Field(None, max_length=255)
    cpf: Optional[str] = Field(None, max_length=14)
    birth_date: Optional[date] = None
    role: Optional[str] = Field(None, pattern=r"^(titular|conjuge|filho|dependente)$")
    order: Optional[int] = Field(None, ge=0)
    extra: Optional[dict[str, object]] = None

    @field_validator("key")
    @classmethod
    def _key(cls, v: str | None) -> str | None:
        return _validate_key_slug_strict(v)

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: str | None) -> str | None:
        return _validate_cpf_11_digits(v)


class BankAccountCreateCommand(BaseModel):
    """Input do ``POST /members/{id}/accounts`` (ADR-226 acrescenta is_joint/co_titulares)."""

    institution_code: str = Field(..., min_length=1, max_length=50)
    account_type: str = Field(..., min_length=1, max_length=100)
    agency: Optional[str] = Field(None, max_length=20)
    account_number: Optional[str] = Field(None, max_length=30)
    label: Optional[str] = Field(None, max_length=255)
    is_joint: bool = False
    co_titulares: Optional[list[str]] = None


class BankAccountUpdateCommand(BankAccountCreateCommand):
    """Input do ``PUT /members/{id}/accounts/{acc_id}`` — semantics replace."""
