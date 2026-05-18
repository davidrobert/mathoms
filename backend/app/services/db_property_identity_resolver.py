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
        """Find ou cria. fix-B2: dedup cross-titular quando endereco_canonical presente."""
        if lookup.endereco_canonical is not None:
            existing = self._find_by_canonical(workspace_id, lookup)
            if existing is not None:
                return _to_record(existing)
        return _to_record(self._insert_row(workspace_id, lookup, first_seen_year, descricao_sample))

    def _find_by_canonical(
        self, workspace_id: str, lookup: PropertyLookupKey
    ) -> PropertyIdentity | None:
        stmt = (
            select(PropertyIdentity)
            .where(
                PropertyIdentity.workspace_id == workspace_id,
                PropertyIdentity.codigo_rfb == lookup.codigo_rfb,
                PropertyIdentity.endereco_canonical == lookup.endereco_canonical,
            )
            .order_by(PropertyIdentity.created_at.asc())
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def _insert_row(
        self,
        workspace_id: str,
        lookup: PropertyLookupKey,
        first_seen_year: int,
        descricao_sample: str,
    ) -> PropertyIdentity:
        row = PropertyIdentity(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            titular_key=lookup.titular_key,
            codigo_rfb=lookup.codigo_rfb,
            endereco_canonical=lookup.endereco_canonical,
            first_seen_year=first_seen_year,
            descricao_sample=descricao_sample,
            low_confidence=lookup.endereco_canonical is None,
        )
        self._session.add(row)
        self._session.flush()
        # Commit imediato libera o writer lock do SQLite (WAL). Sem isso, a
        # sessão long-lived que respaldou o resolver (compartilhada com
        # DBConfigStore em pipeline_task._create_workspace_context) segura o
        # lock até o fim do run e o INSERT do baseline consolidado em
        # stage_session falha com `database is locked` após busy_timeout (30s).
        # Repro prod 2026-05-18 run dadb0cd6. property_identity é identificador
        # globalmente estável — sobrevive a falhas do pipeline by design,
        # então commit eager é semanticamente correto (ADR-215 P2).
        self._session.commit()
        return row


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
