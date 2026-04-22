"""E1.5 output schema — baseline patrimonial extracted from IRPF and property documents."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class PatrimonialItem(BaseModel):
    """A single asset or liability item from the IRPF declaration."""

    code: str = Field(..., description="IRPF item code (e.g. '01' for imóveis, '41' for poupança)")
    description: str = Field(..., description="Item description as in the declaration")
    category: str = Field(
        ...,
        description="Category: imovel, veiculo, investimento, conta_corrente, poupanca, previdencia, outros",
    )
    institution: Optional[str] = Field(None, description="Financial institution name or code")
    value_brl: float = Field(..., description="Value in BRL (as declared)")
    member_key: str = Field(..., description="Key of the family member who owns this item")
    year: int = Field(..., description="Reference tax year")


class BaselinePatrimonialOutput(BaseModel):
    """Structured output for E1.5 — patrimonial baseline from IRPF declarations."""

    items: list[PatrimonialItem] = Field(
        default_factory=list, description="All patrimonial items extracted"
    )
    total_assets_brl: float = Field(0.0, description="Sum of all asset values")
    total_liabilities_brl: float = Field(0.0, description="Sum of all liability values")
    net_worth_brl: float = Field(0.0, description="Total assets - total liabilities")
    reference_year: int = Field(..., description="Tax year of the declaration")
    members_found: list[str] = Field(
        default_factory=list, description="Member keys found in declarations"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: Optional[str] = None
