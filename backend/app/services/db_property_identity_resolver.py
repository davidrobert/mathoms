"""``DBPropertyIdentityResolver`` — adapter SQLAlchemy do `PropertyIdentityResolver` (ADR-215 P2)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import PropertyIdentity
from pipeline.domain.types.property_identity import (
    PropertyIdentityRecord,
    PropertyLookupKey,
)


class DBPropertyIdentityResolver:
    """Idempotent matching/creation de `PropertyIdentity` rows (ADR-215)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def match_or_create(
        self,
        workspace_id: str,
        lookup: PropertyLookupKey,
        first_seen_year: int,
        descricao_sample: str,
    ) -> PropertyIdentityRecord:
        """Find existing row ou cria nova (ADR-215). endereco_canonical=None → low_confidence."""
        # Concorrência: race entre 2 workers gera 2 rows com mesmo lookup;
        # UI de merge resolve manualmente.
        if lookup.endereco_canonical is not None:
            stmt = select(PropertyIdentity).where(
                PropertyIdentity.workspace_id == workspace_id,
                PropertyIdentity.titular_key == lookup.titular_key,
                PropertyIdentity.codigo_rfb == lookup.codigo_rfb,
                PropertyIdentity.endereco_canonical == lookup.endereco_canonical,
            )
            existing = self._session.execute(stmt).scalar_one_or_none()
            if existing is not None:
                return _to_record(existing)

        low_confidence = lookup.endereco_canonical is None
        new_row = PropertyIdentity(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            titular_key=lookup.titular_key,
            codigo_rfb=lookup.codigo_rfb,
            endereco_canonical=lookup.endereco_canonical,
            first_seen_year=first_seen_year,
            descricao_sample=descricao_sample,
            low_confidence=low_confidence,
        )
        self._session.add(new_row)
        self._session.flush()
        return _to_record(new_row)


def _to_record(row: PropertyIdentity) -> PropertyIdentityRecord:
    return PropertyIdentityRecord(
        property_id=row.id,
        workspace_id=row.workspace_id,
        titular_key=row.titular_key,
        codigo_rfb=row.codigo_rfb,
        endereco_canonical=row.endereco_canonical,
        first_seen_year=row.first_seen_year,
        low_confidence=row.low_confidence,
    )
