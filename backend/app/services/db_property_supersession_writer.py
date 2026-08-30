"""``DBPropertySupersessionWriter`` — adapter SQLAlchemy do `PropertySupersessionWriter` (ADR-324)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import PropertyIdentity, WorkspacePropertyOverride
from backend.app.models.property_identity import (
    OVERRIDE_SOURCE_FUZZY_MATCH_ACCEPTED,
    OVERRIDE_SOURCE_MIGRATION_KEYWORD,
    OVERRIDE_SOURCE_USER_MANUAL,
)
from backend.app.services.audit import AuditAction, audit_log_sync
from pipeline.domain.types.property_supersession import (
    SupersessionOutcome,
    SupersessionScope,
)

_logger = logging.getLogger("mathoms.property_identity")

_SOURCE_TRUST = {
    OVERRIDE_SOURCE_MIGRATION_KEYWORD: 0,
    OVERRIDE_SOURCE_FUZZY_MATCH_ACCEPTED: 1,
    OVERRIDE_SOURCE_USER_MANUAL: 2,
}


class DBPropertySupersessionWriter:
    """Reconcile idempotente: estado superseded = função pura do dedup corrente (ADR-324)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def reconcile_supersession(self, scope: SupersessionScope) -> SupersessionOutcome:
        workspace_id = scope.workspace_id
        rows = self._load_rows(workspace_id)
        losers = _losers(rows, scope.winner_by_pid)
        overrides = self._load_overrides(workspace_id)
        repointed, merged = self._repoint_overrides(workspace_id, overrides, losers)
        superseded, cleared = self._reconcile_rows(rows, losers, scope.observed_pids)
        outcome = SupersessionOutcome(
            superseded, cleared, repointed, merged, _unreferenced_live(rows, scope)
        )
        if outcome.changed:
            # Commit eager: mesma racional WAL do DBPropertyIdentityResolver
            # (sessão long-lived seguraria o writer lock do SQLite).
            self._session.commit()
            _log_reconciled(workspace_id, outcome)
        return outcome

    def _load_rows(self, workspace_id: str) -> list[PropertyIdentity]:
        stmt = select(PropertyIdentity).where(PropertyIdentity.workspace_id == workspace_id)
        return list(self._session.execute(stmt).scalars().all())

    def _load_overrides(self, workspace_id: str) -> dict[str, WorkspacePropertyOverride]:
        stmt = select(WorkspacePropertyOverride).where(
            WorkspacePropertyOverride.workspace_id == workspace_id
        )
        return {o.property_id: o for o in self._session.execute(stmt).scalars().all()}

    def _reconcile_rows(
        self,
        rows: list[PropertyIdentity],
        losers: Mapping[str, str],
        observed_pids: frozenset[str],
    ) -> tuple[int, int]:
        superseded = cleared = 0
        now = datetime.now(timezone.utc)
        for row in rows:
            winner_id = losers.get(row.id)
            if winner_id is not None:
                superseded += int(_mark_superseded(row, winner_id, now))
            elif _clear_superseded(row, observed_pids):
                cleared += 1
        return superseded, cleared

    # Repoint puro nunca cria uma 2ª residencia_principal: o partial-unique
    # `uq_workspace_one_residencia_principal` torna esse estado inalcançável no DB,
    # então não há guard a acrescentar aqui.
    #
    # A justificativa original dizia "verificado em 2026-08-11 — o cenário não é nem
    # semeável em teste". Estava certa por acidente: a verificação rodou sobre
    # `Base.metadata.create_all` (`conftest.py`), que declara o índice, enquanto o DB
    # construído por Alembic o tinha PERDIDO desde a `adr235nupropriet1` — em SQLite o
    # estado era semeável, e a decisão de não pôr guard nasceu de uma medição feita no
    # schema errado. O índice foi restaurado em `idxrepair0001` ([[ADR-423]]) e a
    # conclusão passou a ser verdadeira pelo motivo que ela afirma.
    def _repoint_overrides(
        self,
        workspace_id: str,
        overrides: dict[str, WorkspacePropertyOverride],
        losers: Mapping[str, str],
    ) -> tuple[int, int]:
        repointed = merged = 0
        for pid, winner_id in losers.items():
            loser_override = overrides.pop(pid, None)
            if loser_override is None:
                continue
            if winner_id in overrides:
                self._merge_override(workspace_id, loser_override, overrides[winner_id])
                merged += 1
            else:
                loser_override.property_id = winner_id
                overrides[winner_id] = loser_override
                self._session.flush()
                repointed += 1
        return repointed, merged

    # O partial-unique de 1 residencia_principal por workspace é checado
    # por-statement — atualizar a vencedora antes de deletar a perdedora criaria
    # duas RP transitórias e violaria o índice.
    def _merge_override(
        self,
        workspace_id: str,
        loser_override: WorkspacePropertyOverride,
        winner_override: WorkspacePropertyOverride,
    ) -> None:
        perdida = (
            loser_override.classification,
            loser_override.override_source,
            loser_override.updated_at,
        )
        self._session.delete(loser_override)
        self._session.flush()
        if perdida[0] == winner_override.classification:
            return
        self._resolve_conflict(workspace_id, *perdida, winner_override)

    def _resolve_conflict(
        self,
        workspace_id: str,
        loser_classification: str,
        loser_source: str,
        loser_updated_at: datetime | None,
        winner_override: WorkspacePropertyOverride,
    ) -> None:
        loser_wins = _loser_prevails(loser_source, loser_updated_at, winner_override)
        kept = loser_classification if loser_wins else winner_override.classification
        dropped = winner_override.classification if loser_wins else loser_classification
        kept_source = loser_source if loser_wins else winner_override.override_source
        self._audit_merge(workspace_id, winner_override.id, kept, dropped, kept_source)
        if loser_wins:
            winner_override.classification = loser_classification
            winner_override.override_source = loser_source
            self._session.flush()

    def _audit_merge(
        self, workspace_id: str, override_id: str, kept: str, dropped: str, kept_source: str
    ) -> None:
        audit_log_sync(
            self._session,
            action=AuditAction.property_override_supersession_merge,
            resource_type="workspace_property_override",
            resource_id=override_id,
            workspace_id=workspace_id,
            details={"kept": kept, "dropped": dropped, "kept_source": kept_source},
        )


def _mark_superseded(row: PropertyIdentity, winner_id: str, now: datetime) -> bool:
    if row.superseded_at is not None and row.superseded_by_id == winner_id:
        return False
    row.superseded_at = now
    row.superseded_by_id = winner_id
    return True


# Row fora do escopo do run é absorvente (ADR-386): limpar aqui era o que
# revertia, a cada E1.5c, a supersessão feita por sweep.
def _clear_superseded(row: PropertyIdentity, observed_pids: frozenset[str]) -> bool:
    if row.id not in observed_pids:
        return False
    if row.superseded_at is None and row.superseded_by_id is None:
        return False
    row.superseded_at = None
    row.superseded_by_id = None
    return True


# Empate de trust descartava a classificação perdedora em silêncio; quando as
# duas vêm da mesma fonte, o único sinal de intenção do usuário é a recência.
def _loser_prevails(
    loser_source: str,
    loser_updated_at: datetime | None,
    winner: WorkspacePropertyOverride,
) -> bool:
    loser_trust = _SOURCE_TRUST.get(loser_source, 0)
    winner_trust = _SOURCE_TRUST.get(winner.override_source, 0)
    if loser_trust != winner_trust:
        return loser_trust > winner_trust
    if loser_updated_at is None or winner.updated_at is None:
        return False
    return loser_updated_at > winner.updated_at


def _unreferenced_live(rows: list[PropertyIdentity], scope: SupersessionScope) -> int:
    """Vivas que o run não observou — sinal de zumbi acumulando (ADR-386)."""
    return len([r for r in rows if r.superseded_at is None and r.id not in scope.observed_pids])


def _losers(rows: list[PropertyIdentity], winner_by_pid: Mapping[str, str]) -> dict[str, str]:
    known = {row.id for row in rows}
    return {
        pid: winner
        for pid, winner in winner_by_pid.items()
        if pid != winner and pid in known and winner in known
    }


def _log_reconciled(workspace_id: str, outcome: SupersessionOutcome) -> None:
    _logger.info(
        "property_supersession.reconciled",
        extra={
            "workspace_id": workspace_id,
            "superseded": outcome.superseded,
            "cleared": outcome.cleared,
            "overrides_repointed": outcome.overrides_repointed,
            "overrides_merged": outcome.overrides_merged,
        },
    )
