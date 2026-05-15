"""`InMemoryPropertyIdentityResolver` — implementação para testes (ADR-215)."""

from __future__ import annotations

import uuid

from pipeline.domain.types.property_identity import (
    PropertyIdentityRecord,
    PropertyLookupKey,
)


class InMemoryPropertyIdentityResolver:
    """Resolver in-memory para testes unitários de pipeline."""

    def __init__(self) -> None:
        self._rows: list[PropertyIdentityRecord] = []

    def match_or_create(
        self,
        workspace_id: str,
        lookup: PropertyLookupKey,
        first_seen_year: int,
        descricao_sample: str,
    ) -> PropertyIdentityRecord:
        if lookup.endereco_canonical is not None:
            for r in self._rows:
                if (
                    r.workspace_id == workspace_id
                    and r.titular_key == lookup.titular_key
                    and r.codigo_rfb == lookup.codigo_rfb
                    and r.endereco_canonical == lookup.endereco_canonical
                ):
                    return r

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
