"""`InMemoryPropertyIdentityResolver` — implementação para testes (ADR-215, ADR-392)."""

from __future__ import annotations

import uuid

from pipeline.domain.services.property_identity_mint import mint_without_canonical_enabled
from pipeline.domain.types.property_identity import (
    PropertyIdentityRecord,
    PropertyLookupKey,
)


class InMemoryPropertyIdentityResolver:
    """Resolver in-memory — mesma regra de mint que o adapter DB ([[ADR-392]])."""

    def __init__(self) -> None:
        self._rows: list[PropertyIdentityRecord] = []

    def match_or_create(
        self,
        workspace_id: str,
        lookup: PropertyLookupKey,
        first_seen_year: int,
        descricao_sample: str,
    ) -> PropertyIdentityRecord | None:
        hit = _match_canonical(self._rows, workspace_id, lookup)
        if hit is not None:
            return hit
        if lookup.endereco_canonical is None and not mint_without_canonical_enabled():
            return _residual_unique(self._rows, workspace_id, lookup)
        return self._insert(workspace_id, lookup, first_seen_year)

    def _insert(
        self, workspace_id: str, lookup: PropertyLookupKey, first_seen_year: int
    ) -> PropertyIdentityRecord:
        record = PropertyIdentityRecord(
            property_id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            titular_key=lookup.titular_key,
            codigo_rfb=lookup.codigo_rfb,
            endereco_canonical=lookup.endereco_canonical,
            first_seen_year=first_seen_year,
            low_confidence=lookup.endereco_canonical is None,
        )
        self._rows.append(record)
        return record

    def all(self) -> list[PropertyIdentityRecord]:
        return list(self._rows)


def _match_canonical(
    rows: list[PropertyIdentityRecord], workspace_id: str, lookup: PropertyLookupKey
) -> PropertyIdentityRecord | None:
    if lookup.endereco_canonical is None:
        return None
    for row in rows:
        if (
            row.workspace_id == workspace_id
            and row.codigo_rfb == lookup.codigo_rfb
            and row.endereco_canonical == lookup.endereco_canonical
        ):
            return row
    return None


def _residual_unique(
    rows: list[PropertyIdentityRecord], workspace_id: str, lookup: PropertyLookupKey
) -> PropertyIdentityRecord | None:
    hits = [
        row
        for row in rows
        if row.workspace_id == workspace_id
        and row.titular_key == lookup.titular_key
        and row.codigo_rfb == lookup.codigo_rfb
        and row.endereco_canonical is None
    ]
    return hits[0] if len(hits) == 1 else None
