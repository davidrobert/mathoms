"""Command DTOs de ``PropertyMarketValue`` — append-only; correção é nova entry + ``supersede()``."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.app.models.property_market_value import VALID_PMV_SOURCES

PmvSource = Literal[
    "user_declared",
    "avaliacao_terceiros",
    "cep_proxy_futuro",
]

assert set(VALID_PMV_SOURCES) == set(PmvSource.__args__)  # type: ignore[attr-defined]


class PropertyMarketValueCreate(BaseModel):
    """Input de criação de declaração."""

    property_id: str = Field(..., max_length=36)
    valor_brl: Decimal = Field(
        ...,
        gt=0,
        description="Valor de mercado em BRL (string decimal, ADR-090).",
    )
    valuation_date: date
    source: PmvSource = "user_declared"
    confidence: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description=(
            "Confiança 0-1; opcional em user_declared, obrigatório em V2 cep_proxy_futuro."
        ),
    )
    notes: Optional[str] = Field(None, max_length=2000)
