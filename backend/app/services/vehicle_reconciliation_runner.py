"""Runner backend que conecta DB → função pura ``reconcile_baseline_veiculos`` (ADR-239 D3+D4)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as SyncSession

from backend.app.models.vehicle import Vehicle
from pipeline.domain.services.vehicle_reconciliation import (
    ReconciliationConfig,
    ReconciliationSummary,
    reconcile_baseline_veiculos,
    summarize,
)

logger = logging.getLogger("mathoms.vehicles.reconciled")


def reconcile_baseline_with_db(
    workspace_id: str,
    baseline: dict,
    *,
    db: SyncSession,
    config: Optional[ReconciliationConfig] = None,
) -> tuple[dict, ReconciliationSummary]:
    """ADR-239 D3+D4 — query vehicles do workspace e plumbar na função pura."""
    vehicles = _query_active_vehicles(workspace_id, db=db)
    if not vehicles and not baseline.get("veiculos_consolidados"):
        return baseline, summarize([])
    new_baseline, results = reconcile_baseline_veiculos(
        baseline, vehicles, workspace_id, config=config
    )
    summary = summarize(results)
    _log_summary(workspace_id, summary)
    return new_baseline, summary


def _query_active_vehicles(workspace_id: str, *, db: SyncSession) -> list[dict]:
    """Retorna vehicles ativos do workspace em dicts (não exfiltra ORM)."""
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


def _vehicle_to_dict(v: Vehicle) -> dict:
    """Map Vehicle ORM → dict consumido por reconcile_baseline_veiculos."""
    return {
        "id": v.id,
        "workspace_id": v.workspace_id,
        "marca": v.marca,
        "modelo": v.modelo,
        "ano_modelo": v.ano_modelo,
        # member_key ausente — vehicles não associam a family_member (CPF
        # mascarado por LGPD). Blocking por proprietario degrada para
        # "todos candidatos" — comportamento documentado em
        # _filter_by_proprietario quando member_key é falsy.
        "member_key": None,
    }


def _log_summary(workspace_id: str, summary: ReconciliationSummary) -> None:
    """Telemetria LGPD-safe: contagens agregadas, sem PII (placa, CPF, IDs)."""
    logger.info(
        "mathoms.vehicles.reconciled",
        extra={
            "workspace_id": workspace_id,
            "total_items": summary.total_items,
            "matched_count": summary.matched_count,
            "needs_review_count": summary.needs_review_count,
            "no_candidate_count": summary.no_candidate_count,
            "stale_fk_cleared_count": summary.stale_fk_cleared_count,
        },
    )
