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
from pipeline.domain.types.property_supersession import SupersessionOutcome

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

    def reconcile_supersession(
        self,
        workspace_id: str,
        winner_by_pid: Mapping[str, str],
    ) -> SupersessionOutcome:
        rows = self._load_rows(workspace_id)
        losers = _losers(rows, winner_by_pid)
        overrides = self._load_overrides(workspace_id)
        repointed, merged = self._repoint_overrides(workspace_id, overrides, losers)
        superseded, cleared = self._reconcile_rows(rows, losers)
        outcome = SupersessionOutcome(superseded, cleared, repointed, merged)
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
        self, rows: list[PropertyIdentity], losers: Mapping[str, str]
    ) -> tuple[int, int]:
        superseded = cleared = 0
        now = datetime.now(timezone.utc)
        for row in rows:
            winner_id = losers.get(row.id)
            if winner_id is not None:
                if row.superseded_at is None or row.superseded_by_id != winner_id:
                    row.superseded_at = now
                    row.superseded_by_id = winner_id
                    superseded += 1
            elif row.superseded_at is not None or row.superseded_by_id is not None:
                row.superseded_at = None
                row.superseded_by_id = None
                cleared += 1
        return superseded, cleared

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

    def _merge_override(
        self,
        workspace_id: str,
        loser_override: WorkspacePropertyOverride,
        winner_override: WorkspacePropertyOverride,
    ) -> None:
        loser_classification = loser_override.classification
        loser_source = loser_override.override_source
        # O partial-unique de 1 residencia_principal por workspace é checado
        # por-statement — atualizar a vencedora antes de deletar a perdedora
        # criaria duas RP transitórias e violaria o índice.
        self._session.delete(loser_override)
        self._session.flush()
        if loser_classification == winner_override.classification:
            return
        self._resolve_conflict(workspace_id, loser_classification, loser_source, winner_override)

    def _resolve_conflict(
        self,
        workspace_id: str,
        loser_classification: str,
        loser_source: str,
        winner_override: WorkspacePropertyOverride,
    ) -> None:
        loser_wins = _SOURCE_TRUST.get(loser_source, 0) > _SOURCE_TRUST.get(
            winner_override.override_source, 0
        )
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
