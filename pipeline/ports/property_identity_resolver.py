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

    def match(
        self,
        workspace_id: str,
        lookup: PropertyLookupKey,
        descricao_sample: str,
    ) -> PropertyIdentityRecord | None:
        # [[ADR-440]] D6: a mesma cascata de `match_or_create`, sem cunhar — o dry-run
        # que o commit imediato do mint não permite, e o plano do enricher em duas fases.
        ...

    def create(
        self,
        workspace_id: str,
        lookup: PropertyLookupKey,
        first_seen_year: int,
        descricao_sample: str,
    ) -> PropertyIdentityRecord | None:
        # [[ADR-440]] D7: o insert sem a cascata. Depois que o plano vetou uma candidata,
        # re-rodar a cascata reencontraria a row vetada pelo loose (que ignora o código).
        # Sem canonical não minta ([[ADR-392]]).
        ...

    def match_or_create(
        self,
        workspace_id: str,
        lookup: PropertyLookupKey,
        first_seen_year: int,
        descricao_sample: str,
    ) -> PropertyIdentityRecord | None:
        # ADR-392: sem canonical não minta. None = needs_review no item.
        ...
