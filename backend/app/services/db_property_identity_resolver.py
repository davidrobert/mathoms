"""``DBPropertyIdentityResolver`` — adapter SQLAlchemy do `PropertyIdentityResolver` (ADR-215, ADR-225, ADR-265, ADR-375)."""

from __future__ import annotations

import logging
import uuid
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from backend.app.models import PropertyIdentity
from backend.app.repositories.property_repository import all_property_identities_stmt
from backend.app.services.supersession_chain import resolve_supersession_chain
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
    """Idempotent matching/creation de `PropertyIdentity` via cascata estrito→loose→fuzzy→amostra→insert (ADR-215, ADR-225 §2, ADR-265, ADR-375)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def match_or_create(
        self,
        workspace_id: str,
        lookup: PropertyLookupKey,
        first_seen_year: int,
        descricao_sample: str,
    ) -> PropertyIdentityRecord:
        """Match cascade: estrito → loose → fuzzy → amostra bruta → insert (ADR-375)."""
        index = _WorkspaceIdentities(self._load_rows(workspace_id))
        existing = _cascade_match(index, lookup, descricao_sample)
        if existing is not None:
            return _to_record(existing)
        return _to_record(self._insert_row(workspace_id, lookup, first_seen_year, descricao_sample))

    def _load_rows(self, workspace_id: str) -> list[PropertyIdentity]:
        # Carrega vivas E supersedidas: a cascata atravessa o ponteiro em vez de
        # filtrar (ADR-375). Filtrar deixaria a vencedora inalcançável quando a
        # perdedora é quem casa, e o resolver inseriria row nova a cada run.
        stmt = all_property_identities_stmt(workspace_id)
        return list(self._session.execute(stmt).scalars().all())

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


class _WorkspaceIdentities:
    """Rows do workspace + índice de supersessão, montados uma vez por match."""

    def __init__(self, rows: list[PropertyIdentity]) -> None:
        self._by_id = {row.id: row for row in rows}
        self._links = {row.id: (row.superseded_at, row.superseded_by_id) for row in rows}
        self.ordered = sorted(rows, key=lambda row: (row.created_at, row.id))

    def first_live(self, level: str, candidates: Iterable[PropertyIdentity]):
        """Primeiro candidato cuja cadeia de supersessão termina em row viva."""
        for candidate in candidates:
            winner = self._live_winner(candidate)
            if winner is not None:
                _log_hit(level, candidate, winner)
                return winner
        return None

    def _live_winner(self, candidate: PropertyIdentity) -> Optional[PropertyIdentity]:
        winner_id = resolve_supersession_chain(candidate.id, self._links)
        return self._by_id.get(winner_id) if winner_id is not None else None


def _cascade_match(
    index: _WorkspaceIdentities,
    lookup: PropertyLookupKey,
    descricao_sample: str,
) -> Optional[PropertyIdentity]:
    if lookup.endereco_canonical is None:
        return index.first_live(
            "descricao", _candidates_by_descricao(index, lookup, descricao_sample)
        )
    canonical = lookup.endereco_canonical
    return (
        index.first_live("strict", _candidates_strict(index, lookup))
        or index.first_live("loose", _candidates_loose(index, canonical))
        or index.first_live("fuzzy", _candidates_fuzzy(index, canonical, descricao_sample))
    )


def _candidates_strict(
    index: _WorkspaceIdentities, lookup: PropertyLookupKey
) -> list[PropertyIdentity]:
    """Match estrito: codigo_rfb + endereco_canonical (path quente)."""
    return [
        row
        for row in index.ordered
        if row.codigo_rfb == lookup.codigo_rfb
        and row.endereco_canonical == lookup.endereco_canonical
    ]


def _candidates_loose(index: _WorkspaceIdentities, canonical: str) -> list[PropertyIdentity]:
    """Match loose: ignora codigo_rfb. First-write-wins preserva invariante E5 (ADR-225 §2)."""
    return [row for row in index.ordered if row.endereco_canonical == canonical]


def _candidates_fuzzy(
    index: _WorkspaceIdentities, canonical: str, descricao_sample: str
) -> list[PropertyIdentity]:
    """Match fuzzy por proximidade numérica (ADR-265), vivas antes das supersedidas."""
    complemento_in = extract_complemento(descricao_sample)
    hits = [row for row in index.ordered if _fuzzy_matches(canonical, complemento_in, row)]
    # Sort estável: uma row envenenada de era antiga não deve puxar input novo
    # para o vencedor errado quando existe candidata viva equivalente.
    return sorted(hits, key=lambda row: row.superseded_at is not None)


# Substitui o passe fuzzy de low-confidence que a ADR-225 §3 deixou de fora.
# `titular_key` fica fora do predicado de propósito: incluí-lo foi o mecanismo
# que duplicou o imóvel do casal quando a extração variou a grafia do membro.
def _candidates_by_descricao(
    index: _WorkspaceIdentities, lookup: PropertyLookupKey, descricao_sample: str
) -> list[PropertyIdentity]:
    """Amostra bruta byte-exata — piso determinístico quando não há canonical (ADR-375)."""
    if not descricao_sample:
        return []
    return [
        row
        for row in index.ordered
        if row.codigo_rfb == lookup.codigo_rfb
        and row.endereco_canonical is None
        and (row.descricao_sample or "") == descricao_sample
    ]


def _fuzzy_matches(
    canonical: str,
    complemento_in: str | None,
    candidate: PropertyIdentity,
) -> bool:
    if not candidate.endereco_canonical:
        return False
    complemento_other = extract_complemento(candidate.descricao_sample)
    return matches_fuzzy(
        canonical,
        candidate.endereco_canonical,
        complemento_a=complemento_in,
        complemento_b=complemento_other,
    )


def _log_hit(level: str, candidate: PropertyIdentity, winner: PropertyIdentity) -> None:
    _logger.info(
        "property_identity.cascade_hit",
        extra={"level": level, "via_supersession": candidate.id != winner.id},
    )


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
