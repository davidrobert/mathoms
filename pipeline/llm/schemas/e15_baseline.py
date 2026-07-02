"""E1.5 output schema — baseline patrimonial extracted from IRPF and property documents."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _coerce_decimal(v):
    """Boundary LLM monetário = ``Decimal`` (ADR-090/ADR-259 §1): aceita ``int|str|float``
    via ``Decimal(str(v))`` — o prompt v1.2.0 pede string decimal, mas number JSON de
    respostas antigas/reask não pode brickar a extração."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float, str)):
        try:
            return Decimal(str(v))
        except InvalidOperation as exc:
            raise ValueError(
                f"E1.5: valor monetário inválido — esperado string decimal "
                f"'150000.00', recebido {type(v).__name__}={v!r}"
            ) from exc
    raise TypeError(f"E1.5: não consigo coerce {type(v).__name__}={v!r} para Decimal")


class PatrimonialItem(BaseModel):
    """A single asset or liability item from the IRPF declaration."""

    code: str = Field(..., description="IRPF item code (e.g. '01' for imóveis, '41' for poupança)")
    description: str = Field(..., description="Item description as in the declaration")
    category: str = Field(
        ...,
        description="Category: imovel, veiculo, investimento, conta_corrente, poupanca, previdencia, outros",
    )
    institution: Optional[str] = Field(None, description="Financial institution name or code")
    value_brl: Decimal = Field(..., description="Value in BRL as decimal string (e.g. '150000.00')")
    member_key: str = Field(..., description="Key of the family member who owns this item")
    year: int = Field(..., description="Reference tax year")
    # ADR-267: CPF do contribuinte (do campo 'CPF do Contribuinte' da declaração).
    # Identidade canônica primária — sobrevive a casamento/divórcio/abreviação de nome.
    cpf: Optional[str] = Field(
        None,
        description="CPF do contribuinte da declaração (11 dígitos, com ou sem máscara) — ADR-267",
    )

    _coerce_value = field_validator("value_brl", mode="before")(_coerce_decimal)


class BaselinePatrimonialOutput(BaseModel):
    """Structured output for E1.5 — patrimonial baseline from IRPF declarations."""

    items: list[PatrimonialItem] = Field(
        default_factory=list, description="All patrimonial items extracted"
    )
    total_assets_brl: Decimal = Field(
        Decimal("0"), description="Sum of all asset values as decimal string"
    )
    total_liabilities_brl: Decimal = Field(
        Decimal("0"), description="Sum of all liability values as decimal string"
    )
    net_worth_brl: Decimal = Field(
        Decimal("0"), description="Total assets - total liabilities as decimal string"
    )
    reference_year: int = Field(..., description="Tax year of the declaration")
    members_found: list[str] = Field(
        default_factory=list, description="Member keys found in declarations"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: Optional[str] = None

    _coerce_totals = field_validator(
        "total_assets_brl", "total_liabilities_brl", "net_worth_brl", mode="before"
    )(_coerce_decimal)
