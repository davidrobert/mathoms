"""Envelope V1 do snapshot de proteção pinado ao Report (ADR-387)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeline.domain.protection_computation_inputs import ProtectionComputationInputsV1

CALCULATOR_VERSIONS: dict[str, str] = {
    "life_insurance_coverage_ideal": "1",
    "disability_coverage_gap": "1",
    "itcmd_estimated": "1",
    "compliance_risk_us_person": "1",
}

HASH_VERSION_E5_V1 = "e5-v1"
HASH_VERSION_REPORT_V2 = "report-v2"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProtectionComputationSnapshotV1(_StrictModel):
    snapshot_version: Literal[1] = 1
    snapshot_status: Literal["available", "unavailable"]
    reason_code: Literal["source_not_injected", "source_read_failed", "build_failed"] | None = None
    input_contract_version: Literal[1] = 1
    pipeline_run_id: str | None = None
    analysis_artifact_id: int | None = None
    e5_inputs_digest_sha256: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")
    captured_at: datetime
    as_of_date: date
    calculator_versions: dict[str, str]
    inputs: ProtectionComputationInputsV1 | None = None
    bundle: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_availability(self) -> "ProtectionComputationSnapshotV1":
        if self.snapshot_status == "available" and self.reason_code is not None:
            raise ValueError("available snapshot must not carry reason_code")
        if self.snapshot_status == "unavailable" and self.reason_code is None:
            raise ValueError("unavailable snapshot requires reason_code")
        return self


def unavailable_snapshot(**kwargs) -> ProtectionComputationSnapshotV1:
    kwargs.setdefault("calculator_versions", dict(CALCULATOR_VERSIONS))
    kwargs.setdefault("bundle", None)
    return ProtectionComputationSnapshotV1(snapshot_status="unavailable", **kwargs)


__all__ = [
    "CALCULATOR_VERSIONS",
    "HASH_VERSION_E5_V1",
    "HASH_VERSION_REPORT_V2",
    "ProtectionComputationSnapshotV1",
    "unavailable_snapshot",
]
