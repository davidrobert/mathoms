"""E1 output schema — extracted family members from personal documents."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExtractedAccount(BaseModel):
    institution_code: str = Field(
        ..., description="Canonical bank code (e.g. 'itau', 'santander', 'c6bank')"
    )
    account_type: str = Field(
        ..., description="Account type (e.g. 'extratoconta', 'cartao_credito', 'investimento')"
    )
    agency: Optional[str] = None
    account_number: Optional[str] = None


class ExtractedMember(BaseModel):
    key: str = Field(
        ...,
        description="Short canonical key for this member (lowercase, no accents, e.g. 'david', 'mariana')",
    )
    full_name: str = Field(..., description="Full legal name as it appears in documents")
    short_name: str = Field(..., description="Short display name (first name)")
    # ADR-259 §2 (A20.l15): o VALOR do CPF nunca sai do LLM — só o sinal de
    # presença. O valor é extraído por regex do documento original pelo
    # adapter backend (family_member_pii_service) e cifrado via Fernet.
    cpf_present: bool = Field(
        False, description="True when the document contains this member's CPF (NEVER the value)"
    )
    birth_date: Optional[str] = Field(None, description="Birth date in YYYY-MM-DD format")
    role: str = Field("titular", description="Role: titular, conjuge, filho, dependente")
    accounts: list[ExtractedAccount] = Field(default_factory=list)


class MembersExtractOutput(BaseModel):
    """Structured output for E1 — member extraction from personal documents."""

    members: list[ExtractedMember] = Field(
        ..., min_length=1, description="Extracted family members"
    )
    titular_key: Optional[str] = Field(None, description="Key of the primary account holder")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall extraction confidence (0-1)"
    )
    notes: Optional[str] = Field(
        None, description="Any relevant notes about extraction quality or ambiguities"
    )
