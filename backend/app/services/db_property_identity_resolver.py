"""``DBPropertyIdentityResolver`` — adapter SQLAlchemy do `PropertyIdentityResolver` (ADR-215, ADR-225, ADR-265)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import PropertyIdentity
from pipeline.domain.services.canonical_fuzzy_match import (
    extract_complemento,
    matches_fuzzy,
)
from pipeline.domain.types.property_identity import (
    PropertyIdentityRecord,
    PropertyLookupKey,
)

_logger = logging.getLogger("mathoms.property_identity")


class DBPropertyIdentityResolver:
    """Idempotent matching/creation de `PropertyIdentity` rows via cascata estrito→loose→fuzzy→insert (ADR-215, ADR-225 §2, ADR-265)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def match_or_create(
        self,
        workspace_id: str,
        lookup: PropertyLookupKey,
        first_seen_year: int,
        descricao_sample: str,
    ) -> PropertyIdentityRecord:
        """Match cascade: estrito → loose → fuzzy → insert (ADR-265)."""
        existing = self._cascade_match(workspace_id, lookup, descricao_sample)
        if existing is not None:
            return _to_record(existing)
        return _to_record(self._insert_row(workspace_id, lookup, first_seen_year, descricao_sample))

    def _cascade_match(
        self, workspace_id: str, lookup: PropertyLookupKey, descricao_sample: str
    ) -> PropertyIdentity | None:
        if lookup.endereco_canonical is None:
            return None
        canonical = lookup.endereco_canonical
        return (
            _log_hit("strict", self._find_by_canonical_strict(workspace_id, lookup))
            or _log_hit("loose", self._find_by_canonical_loose(workspace_id, canonical))
            or _log_hit(
                "fuzzy", self._find_by_canonical_fuzzy(workspace_id, canonical, descricao_sample)
            )
        )

    def _find_by_canonical_strict(
        self, workspace_id: str, lookup: PropertyLookupKey
    ) -> PropertyIdentity | None:
        """Match estrito: codigo_rfb + endereco_canonical (path quente)."""
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

    def _find_by_canonical_loose(
        self, workspace_id: str, endereco_canonical: str
    ) -> PropertyIdentity | None:
        """Match loose: ignora codigo_rfb. First-write-wins preserva invariante E5 (ADR-225 §2)."""
        stmt = (
            select(PropertyIdentity)
            .where(
                PropertyIdentity.workspace_id == workspace_id,
                PropertyIdentity.endereco_canonical == endereco_canonical,
            )
            .order_by(PropertyIdentity.created_at.asc())
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def _find_by_canonical_fuzzy(
        self,
        workspace_id: str,
        endereco_canonical: str,
        descricao_sample: str,
    ) -> PropertyIdentity | None:
        """Match fuzzy por proximidade numérica (ADR-265)."""
        complemento_in = extract_complemento(descricao_sample)
        for candidate in self._iter_candidates(workspace_id):
            if self._fuzzy_matches(endereco_canonical, complemento_in, candidate):
                return candidate
        return None

    def _iter_candidates(self, workspace_id: str):
        stmt = (
            select(PropertyIdentity)
            .where(PropertyIdentity.workspace_id == workspace_id)
            .order_by(PropertyIdentity.created_at.asc())
        )
        return self._session.execute(stmt).scalars()

    def _fuzzy_matches(
        self,
        endereco_canonical: str,
        complemento_in: str | None,
        candidate: PropertyIdentity,
    ) -> bool:
        if not candidate.endereco_canonical:
            return False
        complemento_other = extract_complemento(candidate.descricao_sample)
        return matches_fuzzy(
            endereco_canonical,
            candidate.endereco_canonical,
            complemento_a=complemento_in,
            complemento_b=complemento_other,
        )

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


def _log_hit(level: str, row: PropertyIdentity | None) -> PropertyIdentity | None:
    if row is not None:
        _logger.info("property_identity.cascade_hit", extra={"level": level})
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
