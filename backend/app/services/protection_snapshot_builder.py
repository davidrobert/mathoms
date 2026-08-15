"""Monta o envelope V1 a partir do E5 pinado — sem consultar estado live."""

from __future__ import annotations

from datetime import date, datetime, timezone

from backend.app.core.logging import get_logger
from pipeline.domain.protection_computation_inputs import (
    ProtectionComputationInputsV1,
    analysis_clock,
)
from pipeline.domain.protection_computation_snapshot import (
    CALCULATOR_VERSIONS,
    ProtectionComputationSnapshotV1,
    unavailable_snapshot,
)

logger = get_logger("mathoms.protection.snapshot")


def build_protection_snapshot(
    *,
    e5_payload: dict,
    pipeline_run_id: str | None,
    analysis_artifact_id: int | None,
) -> dict:
    """Fotografia do run. Erro técnico vira envelope unavailable, nunca live."""
    captured_at, as_of_date = _clock_from_e5(e5_payload)
    ids = {"pipeline_run_id": pipeline_run_id, "analysis_artifact_id": analysis_artifact_id}
    try:
        return _build_from_e5(e5_payload, captured_at=captured_at, as_of_date=as_of_date, **ids)
    except Exception:
        logger.exception("protection_snapshot_build_failed", extra=ids)
        return unavailable_snapshot(
            captured_at=captured_at, as_of_date=as_of_date, reason_code="build_failed", **ids
        ).model_dump(mode="json")


def protection_bundle_from_snapshot(raw: dict | None) -> dict | None:
    """GET só lê o bundle persistido. None = Report legado."""
    if raw is None:
        return None
    bundle = raw.get("bundle")
    return bundle if isinstance(bundle, dict) else None


def _clock_from_e5(e5_payload: dict) -> tuple[datetime, date]:
    data_analise = e5_payload.get("data_analise")
    if isinstance(data_analise, str) and len(data_analise) >= 10:
        return analysis_clock(data_analise)
    today = date.today()
    return datetime(today.year, today.month, today.day, tzinfo=timezone.utc), today


def _parse_inputs(raw: object) -> ProtectionComputationInputsV1 | None:
    if not isinstance(raw, dict):
        return None
    return ProtectionComputationInputsV1.model_validate(raw)


def _unavailable_from_inputs(inputs, *, captured_at, as_of_date, **ids):
    reason = "source_not_injected"
    if inputs is not None and inputs.reason_code is not None:
        reason = inputs.reason_code
    digest = None if inputs is None else inputs.inputs_digest_sha256
    return unavailable_snapshot(
        captured_at=captured_at,
        as_of_date=as_of_date,
        reason_code=reason,
        e5_inputs_digest_sha256=digest,
        inputs=inputs,
        **ids,
    )


def _build_from_e5(e5_payload: dict, *, captured_at, as_of_date, **ids) -> dict:
    inputs = _parse_inputs(e5_payload.get("protection_computation_inputs_v1"))
    if inputs is None or inputs.status != "available":
        return _unavailable_from_inputs(
            inputs, captured_at=captured_at, as_of_date=as_of_date, **ids
        ).model_dump(mode="json")
    return ProtectionComputationSnapshotV1(
        snapshot_status="available",
        e5_inputs_digest_sha256=inputs.inputs_digest_sha256,
        captured_at=captured_at,
        as_of_date=as_of_date,
        calculator_versions=dict(CALCULATOR_VERSIONS),
        inputs=inputs,
        bundle=None,
        **ids,
    ).model_dump(mode="json")


__all__ = [
    "build_protection_snapshot",
    "protection_bundle_from_snapshot",
]
