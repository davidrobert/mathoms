"""Response DTOs do agregado Property (ADR-215 P4)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PropertyResponse(BaseModel):
    """Snapshot read-model de um imóvel classificável."""

    model_config = ConfigDict(extra="forbid")

    property_id: str
    titular_key: str
    codigo_rfb: str
    descricao_sample: Optional[str] = None
    endereco_canonical: Optional[str] = None
    first_seen_year: int
    low_confidence: bool

    # Classification atual (None se ainda não há override)
    classification: Optional[str] = None
    override_source: Optional[str] = None
    classification_set_at: Optional[datetime] = None

    # Score 0-100 do fuzzy match contra contribuinte.endereco. None quando
    # não há endereço extraído do IRPF (fallback).
    suggested_score: Optional[int] = None
    suggested_residencia_principal: bool = False


class PropertyListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    residencia_status: str
    imoveis_no_if: bool = True
    # `null` = default herdado (ADR-223 §1 conservador); timestamp = escolha
    # explícita do usuário. Frontend usa pra distinguir banner one-time.
    imoveis_no_if_set_at: Optional[datetime] = None
    properties: list[PropertyResponse]


class ResidenciaStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    status: str


class ImoveisNoIfResponse(BaseModel):
    """`PUT /workspaces/{ws}/imoveis-no-if` response (ADR-222)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    imoveis_no_if: bool
    # `set_at IS None` ↔ default migrado; `set_at` populado ↔ escolha explícita.
    set_at: Optional[datetime] = None
    set_by_user_id: Optional[str] = None
