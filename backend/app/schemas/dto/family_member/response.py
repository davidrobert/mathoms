"""Response DTOs do agregado ``FamilyMember``.

Wire shape retornado pela API — mudanças aqui são **breaking** para o
frontend (`lib/api.ts` / report React). Compat binária com
``schemas.config.FamilyMemberSchema`` é preservada durante A6e; o tipo
legado re-exporta estes durante a janela de transição.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BankAccountResponse(BaseModel):
    """Conta bancária ligada a um membro (ADR-226 acrescenta is_joint/co_titulares)."""

    id: Optional[str] = None
    institution_code: str = Field(..., min_length=1, max_length=50)
    account_type: str = Field(..., min_length=1, max_length=100)
    agency: Optional[str] = Field(None, max_length=20)
    account_number: Optional[str] = Field(None, max_length=30)
    label: Optional[str] = Field(None, max_length=255)
    is_joint: bool = False
    co_titulares: Optional[list[str]] = None

    model_config = {"from_attributes": True}


class FamilyMemberResponse(BaseModel):
    """Membro da família com contas bancárias eager-loaded."""

    id: Optional[str] = None
    key: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Chave curta canônica (ex.: 'david', 'mariana').",
    )
    full_name: str = Field(..., min_length=1, max_length=255)
    short_name: str = Field(..., min_length=1, max_length=100)
    birth_name: Optional[str] = Field(
        None,
        max_length=255,
        description=(
            "Nome civil anterior / de nascimento (usado para reconciliar contas "
            "antigas). Persiste em ``extra.nome_nascimento``."
        ),
    )
    cpf: Optional[str] = Field(
        None,
        max_length=14,
        description="CPF em plaintext (decriptado do vault ao responder).",
    )
    birth_date: Optional[date] = None
    role: str = Field(..., pattern=r"^(titular|conjuge|filho|dependente)$")
    order: int = Field(default=0, ge=0)
    extra: Optional[dict[str, object]] = Field(
        None,
        description=(
            "Campos extras arbitrários (variantes_nome, regex_nome_fatura, profissao, etc.)."
        ),
    )
    accounts: list[BankAccountResponse] = Field(default_factory=list)

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


class FamilyMemberListResponse(BaseModel):
    """Wrapper paginação-ready para ``GET /members``."""

    members: list[FamilyMemberResponse]
    total: int
