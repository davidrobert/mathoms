"""Tipos de identidade de imóvel cross-IRPFs (ADR-215)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

_SUBCODIGO_IMOVEL = re.compile(r"\d{2}")


@dataclass(frozen=True)
class PropertyLookupKey:
    """Chave composta para matching em `property_identity` (ADR-215)."""

    # endereco_canonical=None força low_confidence (sem endereço estruturado).
    titular_key: str
    codigo_rfb: str
    endereco_canonical: Optional[str]

    # Invariante de domínio, não espelho do VARCHAR(4): quem monta a chave normaliza
    # antes (`subcodigo_imovel_rfb`). Grafia crua aqui é erro de programação — em
    # Postgres ela só estouraria no INSERT, depois de commitadas as rows anteriores.
    def __post_init__(self) -> None:
        if not _SUBCODIGO_IMOVEL.fullmatch(self.codigo_rfb or ""):
            raise ValueError(
                f"expected codigo_rfb as 2-digit imóvel sub-code like '11', "
                f"got {self.codigo_rfb!r}"
            )


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
    # [[ADR-440]] D6: o veto por unidade lê a unidade da row na amostra gravada, e o
    # desempate entre rows admissíveis é a mais antiga (o first-write-wins de hoje).
    descricao_sample: Optional[str] = None
    created_at: Optional[datetime] = None
