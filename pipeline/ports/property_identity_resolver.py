"""`PropertyIdentityResolver` — protocolo de identidade cross-IRPF (ADR-215)."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from pipeline.domain.types.property_identity import (
    PropertyIdentityRecord,
    PropertyLookupKey,
)


@runtime_checkable
class PropertyIdentityResolver(Protocol):
    """Boundary para identidade UUID estável de imóveis cross-IRPFs."""

    def match_or_create(
        self,
        workspace_id: str,
        lookup: PropertyLookupKey,
        first_seen_year: int,
        descricao_sample: str,
    ) -> PropertyIdentityRecord:
        # ADR-215: retorna identidade existente (mesmo lookup) ou cria nova.
        # endereco_canonical=None → low_confidence=True (UI resolve merge).
        ...
