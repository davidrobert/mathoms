"""Response DTOs do agregado ``FamilyMember``.

Wire shape retornado pela API — mudanças aqui são **breaking** para o
frontend (`lib/api.ts` / report React). Compat binária com
``schemas.config.FamilyMemberSchema`` é preservada durante A6e; o tipo
legado re-exporta estes durante a janela de transição.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

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


class CpfMaskedResponse(BaseModel):
    """``GET /members/{id}/cpf`` — máscara canônica, visível a qualquer role (ADR-259 §4)."""

    cpf_masked: str = Field(..., max_length=20, examples=["***.***.789-00"])


class CpfFullResponse(BaseModel):
    """``GET /members/{id}/cpf/full`` — CPF completo, owner-only + auditado (ADR-259 §4)."""

    cpf_full: str = Field(..., max_length=14)


class IrpfSuggestionItem(BaseModel):
    """Item de sugestão de conta extraída de IRPF (ADR-229 §4)."""

    institution_code: str = Field(..., max_length=50)
    institution_label: str = Field(..., max_length=255)
    account_type: str = Field(..., max_length=100)
    agency: Optional[str] = Field(None, max_length=20)
    account_number_raw: Optional[str] = Field(None, max_length=50)
    account_number_norm: Optional[str] = Field(None, max_length=30)
    member_key: str = Field(..., max_length=50)
    member_full_name: str = Field(..., max_length=255)
    cpf_titular_masked: Optional[str] = Field(
        None,
        max_length=20,
        description="CPF do titular IRPF mascarado (ex.: ***.123.456-**).",
    )
    irpf_year: int = Field(..., ge=2000, le=2100)
    match_kind: Literal["new", "partial_collision"]
    collision_with_account_id: Optional[str] = Field(None, max_length=36)


class SuggestionsFromIrpfResponse(BaseModel):
    """Response do ``GET /members/suggestions-from-irpf`` (ADR-229 §4)."""

    irpf_year: int = Field(
        ...,
        description=(
            "Ano-base do IRPF mais recente processado para o workspace. "
            "0 quando o workspace ainda não tem artifact E1."
        ),
    )
    processed_at: Optional[datetime] = None
    suggestions: list[IrpfSuggestionItem] = Field(default_factory=list)
    total_filtered_exact_match: int = 0
    total_dismissed: int = 0
