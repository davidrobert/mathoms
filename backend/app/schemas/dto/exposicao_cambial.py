"""Response DTOs do card Exposição Cambial V2 (ADR-224 §5; read-time service-layer; ADR-090: Decimal string no wire). `share_pct` e `pct_investivel_financeiro` são taxas em [0..100], não monetárias."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ExposicaoCambialPorMoedaDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    moeda: str
    valor_brl: Decimal
    # taxa em [0..100], não monetária — share dentro da exposição
    share_pct: float


class ExposicaoCambialAtivoDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str
    moeda: str
    valor_brl: Decimal
    tipo: str
    lastro_source: str = Field(
        ...,
        description="'override' | 'catalog' | 'fallback_classe' — auditável no card.",
    )


class ExposicaoCambialResponse(BaseModel):
    """Resposta do `GET /v1/workspaces/{ws}/cards/exposicao-cambial`."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    total_brl: Decimal
    # taxa em [0..100], não monetária — share do investível financeiro
    pct_investivel_financeiro: float
    por_moeda: list[ExposicaoCambialPorMoedaDTO]
    tier: str  # verde | amarelo | vermelho | empty
    ativos_contribuintes: list[ExposicaoCambialAtivoDTO]
    catalog_version: int = 1
    source_run_id: Optional[str] = None
    computed_at: datetime
