"""ADR-387 PR2: snapshot pinado ao Report; GET não consulta estado live."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.app.services.protection_snapshot_builder import (
    build_protection_snapshot,
    protection_bundle_from_snapshot,
)
from backend.app.services.report_publication import (
    compute_immutable_hash,
    compute_report_v2_hash,
)
from pipeline.domain.protection_computation_inputs import finalize_inputs
from pipeline.domain.protection_computation_snapshot import HASH_VERSION_REPORT_V2


def _e5(*, inputs=None) -> dict:
    payload = {"data_analise": "2026-08-15", "score": {"valor": 7}}
    if inputs is not None:
        payload["protection_computation_inputs_v1"] = inputs.model_dump(mode="json")
    return payload


def test_builder_unavailable_when_e5_did_not_inject_sources() -> None:
    snap = build_protection_snapshot(
        e5_payload=_e5(),
        pipeline_run_id="run-1",
        analysis_artifact_id=9,
    )
    assert snap["snapshot_status"] == "unavailable"
    assert snap["reason_code"] == "source_not_injected"
    assert snap["bundle"] is None
    assert protection_bundle_from_snapshot(snap) is None


def test_builder_available_when_e5_carries_available_inputs() -> None:
    inputs = finalize_inputs(
        status="available",
        captured_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        as_of_date=date(2026, 8, 15),
        pipeline_run_id="run-1",
    )
    snap = build_protection_snapshot(
        e5_payload=_e5(inputs=inputs),
        pipeline_run_id="run-1",
        analysis_artifact_id=9,
    )
    assert snap["snapshot_status"] == "available"
    assert snap["e5_inputs_digest_sha256"] == inputs.inputs_digest_sha256
    assert snap["bundle"] is None


def test_legacy_report_has_null_bundle() -> None:
    assert protection_bundle_from_snapshot(None) is None


def test_report_v2_hash_changes_with_snapshot_not_with_e5_volatile() -> None:
    e5_a = {"score": 7, "generated_at": "2026-08-15T10:00:00Z"}
    e5_b = {"score": 7, "generated_at": "2026-08-15T11:00:00Z"}
    snap = {"snapshot_version": 1, "bundle": None}
    other = {"snapshot_version": 1, "bundle": {"policies": []}}
    assert compute_report_v2_hash(e5_a, snap) == compute_report_v2_hash(e5_b, snap)
    assert compute_report_v2_hash(e5_a, snap) != compute_report_v2_hash(e5_a, other)
    assert compute_immutable_hash(e5_a) == compute_immutable_hash(e5_b)
    assert HASH_VERSION_REPORT_V2 == "report-v2"


def test_report_v2_hash_ignores_key_order_in_snapshot() -> None:
    e5 = {"score": 7}
    a = {"bundle": None, "snapshot_version": 1}
    b = {"snapshot_version": 1, "bundle": None}
    assert compute_report_v2_hash(e5, a) == compute_report_v2_hash(e5, b)


async def _add_analysis_artifact(db, ws, run):
    from backend.app.models.pipeline_artifact import PipelineArtifact

    artifact = PipelineArtifact(
        workspace_id=ws.id,
        pipeline_run_id=run.id,
        stage="analyze_finances",
        artifact_key="analise_financeira",
        content_json={"data_analise": "2026-08-15", "score": {"valor": 7}},
    )
    db.add(artifact)
    await db.flush()
    return artifact


async def _seed_analysis_report(db, *, snapshot: dict | None):
    from backend.tests import factories

    ws = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=ws)
    artifact = await _add_analysis_artifact(db, ws, run)
    report = await factories.make_report(
        db, workspace=ws, pipeline_run=run, analysis_artifact_id=artifact.id
    )
    report.protection_snapshot_json = snapshot
    await db.commit()
    return ws, report


@pytest.mark.asyncio
async def test_get_report_data_injects_persisted_bundle_only(db) -> None:
    import json

    from backend.app.application.report.get_report_data import get_report_data

    bundle = {"policies": [], "gap_analysis": {}}
    ws, report = await _seed_analysis_report(
        db,
        snapshot={
            "snapshot_version": 1,
            "snapshot_status": "unavailable",
            "reason_code": "source_not_injected",
            "bundle": bundle,
        },
    )
    payload = json.loads((await get_report_data(ws.id, report.id, db=db)).body)
    assert payload["protection_bundle"] == bundle


@pytest.mark.asyncio
async def test_get_report_data_legacy_report_serves_null_bundle(db) -> None:
    import json

    from backend.app.application.report.get_report_data import get_report_data

    ws, report = await _seed_analysis_report(db, snapshot=None)
    payload = json.loads((await get_report_data(ws.id, report.id, db=db)).body)
    assert payload["protection_bundle"] is None
