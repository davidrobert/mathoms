"""Upsert de Vehicle a partir de CRLVPayload — identidade imutável ADR-239 D1."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as SyncSession

from backend.app.models.vehicle import Vehicle

logger = logging.getLogger("mathoms.vehicles.upsert")


class UpsertOutcome(str, Enum):
    """Resultado de upsert (ADR-239 D1 + D4)."""

    inserted = "inserted"
    updated = "updated"
    needs_review = "needs_review"  # mismatch placa↔renavam


@dataclass(frozen=True)
class UpsertResult:
    """Resultado tipado: ``vehicle`` é None só quando ``outcome == needs_review``."""

    outcome: UpsertOutcome
    vehicle: Optional[Vehicle]
    reason: Optional[str] = None


# Campos editáveis em UPDATE — preserva identidade (placa, renavam, marca, modelo,
# ano_modelo, ano_fabricacao) e overrides user-supplied (codigo_rfb mantém).
_UPDATABLE_FIELDS: tuple[str, ...] = ("cor", "combustivel", "fipe_code")


def _normalize_placa(raw: str) -> str:
    return (raw or "").upper().replace("-", "").replace(" ", "")


def upsert_vehicle_from_payload(
    workspace_id: str, payload: dict, *, db: SyncSession
) -> UpsertResult:
    """ADR-239 D1: upsert por ``(workspace_id, placa)`` com identidade imutável."""
    placa = _normalize_placa(payload.get("placa") or "")
    renavam = payload.get("renavam") or ""
    if not placa or not renavam:
        return UpsertResult(UpsertOutcome.needs_review, None, "payload sem placa ou renavam")
    existing = _find_by_placa(workspace_id, placa, db=db)
    if existing is None:
        return _insert(workspace_id, placa, renavam, payload, db=db)
    if existing.renavam != renavam:
        # ADR-239 D4 dedupe hierárquico: colisão placa↔renavam diferente.
        return UpsertResult(
            UpsertOutcome.needs_review,
            existing,
            f"placa {placa} já cadastrada com RENAVAM diferente — revisão humana",
        )
    return _update(existing, payload, db=db)


def _find_by_placa(workspace_id: str, placa: str, *, db: SyncSession) -> Optional[Vehicle]:
    return db.execute(
        select(Vehicle).where(Vehicle.workspace_id == workspace_id, Vehicle.placa == placa)
    ).scalar_one_or_none()


def _build_vehicle(workspace_id: str, placa: str, renavam: str, payload: dict) -> Vehicle:
    return Vehicle(
        workspace_id=workspace_id,
        placa=placa,
        renavam=renavam,
        marca=payload.get("marca", ""),
        modelo=payload.get("modelo", ""),
        ano_modelo=int(payload.get("ano_modelo", 0)),
        ano_fabricacao=int(payload.get("ano_fabricacao", 0)),
        cor=payload.get("cor"),
        combustivel=payload.get("combustivel"),
        fipe_code=payload.get("fipe_code"),
    )


def _insert(
    workspace_id: str, placa: str, renavam: str, payload: dict, *, db: SyncSession
) -> UpsertResult:
    vehicle = _build_vehicle(workspace_id, placa, renavam, payload)
    db.add(vehicle)
    db.flush()
    _log_outcome(workspace_id, "inserted", placa)
    return UpsertResult(UpsertOutcome.inserted, vehicle, None)


def _apply_updates(existing: Vehicle, payload: dict) -> bool:
    """Aplica updates em campos editáveis; retorna True se algo mudou."""
    changed = False
    for field in _UPDATABLE_FIELDS:
        new_value = payload.get(field)
        if new_value is None or getattr(existing, field) == new_value:
            continue
        setattr(existing, field, new_value)
        changed = True
    return changed


def _update(existing: Vehicle, payload: dict, *, db: SyncSession) -> UpsertResult:
    """Atualiza apenas campos não-identidade (cor, combustivel, fipe_code)."""
    if _apply_updates(existing, payload):
        existing.updated_at = datetime.now(timezone.utc)
        db.flush()
        _log_outcome(existing.workspace_id, "updated", existing.placa)
    else:
        _log_outcome(existing.workspace_id, "noop", existing.placa)
    return UpsertResult(UpsertOutcome.updated, existing, None)


def _log_outcome(workspace_id: str, outcome: str, placa: str) -> None:
    logger.info(
        "mathoms.vehicles.upserted",
        extra={"workspace_id": workspace_id, "outcome": outcome, "placa_redacted": _mask(placa)},
    )


def _mask(placa: str) -> str:
    """Mask placa para log (LGPD ADR-231 alinhado — placa é PII fraca mas evitamos)."""
    if len(placa) < 4:
        return "***"
    return f"{placa[:3]}***{placa[-1]}"
