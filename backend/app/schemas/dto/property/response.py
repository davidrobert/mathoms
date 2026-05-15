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
    properties: list[PropertyResponse]


class ResidenciaStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    status: str
