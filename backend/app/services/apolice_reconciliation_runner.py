"""Runner backend reconciliação apolice → vehicle/property (ADR-239 D3)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as SyncSession

from backend.app.models.property_identity import PropertyIdentity
from backend.app.models.vehicle import Vehicle
from backend.app.repositories.property_repository import live_property_identities_stmt
from pipeline.domain.services.apolice_reconciliation import (
    ApoliceReconciliationSummary,
    reconcile_apolice_bens,
    summarize_apolice,
)

logger = logging.getLogger("mathoms.apolice.reconciled")


def reconcile_apolice_with_db(
    workspace_id: str,
    apolice_payload: dict,
    *,
    db: SyncSession,
) -> tuple[dict, ApoliceReconciliationSummary]:
    """ADR-239 D3 — query vehicles + property_identity e plumba na função pura."""
    vehicles = _query_active_vehicles(workspace_id, db=db)
    properties = _query_property_identities(workspace_id, db=db)
    bens = apolice_payload.get("bens_segurados") or []
    if not bens:
        return apolice_payload, summarize_apolice([])
    new_payload, results = reconcile_apolice_bens(
        apolice_payload, vehicles, properties, workspace_id
    )
    summary = summarize_apolice(results)
    _log_summary(workspace_id, summary)
    return new_payload, summary


def _query_active_vehicles(workspace_id: str, *, db: SyncSession) -> list[dict]:
    rows = (
        db.execute(
            select(Vehicle).where(
                Vehicle.workspace_id == workspace_id,
                Vehicle.archived_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    return [_vehicle_to_dict(v) for v in rows]


def _query_property_identities(workspace_id: str, *, db: SyncSession) -> list[dict]:
    rows = db.execute(live_property_identities_stmt(workspace_id)).scalars().all()
    return [_property_to_dict(p) for p in rows]


def _vehicle_to_dict(v: Vehicle) -> dict:
    return {
        "id": v.id,
        "workspace_id": v.workspace_id,
        "placa": v.placa,
    }


def _property_to_dict(p: PropertyIdentity) -> dict:
    return {
        "id": p.id,
        "workspace_id": p.workspace_id,
        "endereco_canonical": p.endereco_canonical or "",
    }


def _log_summary(workspace_id: str, summary: ApoliceReconciliationSummary) -> None:
    """Telemetria LGPD-safe (sem placa, CPF, ID)."""
    logger.info(
        "mathoms.apolice.reconciled",
        extra={
            "workspace_id": workspace_id,
            "total_bens": summary.total_bens,
            "matched": summary.matched,
            "no_candidate": summary.no_candidate,
            "stale_cleared": summary.stale_cleared,
            "idempotent_skip": summary.idempotent_skip,
        },
    )
