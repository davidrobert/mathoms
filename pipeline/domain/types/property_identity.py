"""Tipos de identidade de imóvel cross-IRPFs (ADR-215)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PropertyLookupKey:
    """Chave composta para matching em `property_identity` (ADR-215)."""

    # endereco_canonical=None força low_confidence (sem endereço estruturado).
    titular_key: str
    codigo_rfb: str
    endereco_canonical: Optional[str]


@dataclass(frozen=True)
class PropertyIdentityRecord:
    """Snapshot read-only do row em `property_identity` retornado pelo resolver."""

    property_id: str
    workspace_id: str
    titular_key: str
    codigo_rfb: str
    endereco_canonical: Optional[str]
    first_seen_year: int
    low_confidence: bool
