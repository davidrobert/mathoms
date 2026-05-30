"""Tests Fase 2 (ADR-272) — adapter materializa review_reasons em DB real (SQLite via TestSyncSession, nunca mock): consolidação 1-por-(run,code), occurrence_count agregado, cap e query-mãe."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy import select, text

from backend.app.core.database import Base
from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.review_reason import ReviewReason
from backend.app.tasks.pipeline_task import (
    _REVIEW_REASON_ROW_CAP,
    _materialize_review_reasons,
    _record_stage_needs_review,
)
from backend.tests.conftest import TestSyncSession, _sync_test_engine


@pytest.fixture
def sync_db():
    # TestSyncSession (engine síncrono) não enxerga tabelas criadas pelo engine
    # async do setup_db (WAL cross-connection); cria o schema no engine síncrono.
    Base.metadata.create_all(_sync_test_engine)
    session = TestSyncSession()
    try:
        yield session
    finally:
        session.close()


@dataclass
class _FakeStageResult:
    detail: dict[str, Any] | None


def _reason(code: str, *, occ: int = 1, **over) -> dict:
    base = {
        "code": code,
        "stage": "extract_baseline",
        "artifact_key": "irpfdeclaracao_2024",  # gitleaks:allow — artifact-key fixture, não secret
        "document_id": None,
        "offending_value": "index=0",
        "expected": "x",
        "message": "y",
        "occurrence_count": occ,
    }
    base.update(over)
    return base


def _rows(db, run_id: str) -> list[ReviewReason]:
    return (
        db.execute(select(ReviewReason).where(ReviewReason.pipeline_run_id == run_id))
        .scalars()
        .all()
    )


def _count(db, run_id: str) -> int:
    return len(_rows(db, run_id))


def _materialize(db, run_id: str, ws_id: str, reasons: list[dict]) -> int:
    inserted = _materialize_review_reasons(
        db, run_id=run_id, workspace_id=ws_id, stage_name="extract_baseline", reasons=reasons
    )
    db.commit()
    return inserted


def _explain_plan(db, *, ws_id: str, run_id: str, code: str) -> str:
    plan = db.execute(
        text(
            "EXPLAIN QUERY PLAN SELECT * FROM review_reasons "
            "WHERE workspace_id=:w AND pipeline_run_id=:r AND code=:c"
        ),
        {"w": ws_id, "r": run_id, "c": code},
    ).fetchall()
    return " ".join(str(r) for r in plan).lower()


def _seed_run(db, *, run_id: str, ws_id: str, log_id: str) -> None:
    db.add(PipelineRun(id=run_id, workspace_id=ws_id, status=PipelineRunStatus.running))
    db.add(
        PipelineStageLog(
            id=log_id,
            pipeline_run_id=run_id,
            stage="extract_baseline",
            status=PipelineStageStatus.running,
        )
    )
    db.commit()


def test_consolidates_same_code_to_single_row(sync_db) -> None:
    ws_id, run_id = str(uuid.uuid4()), str(uuid.uuid4())
    reasons = [
        _reason("extract.missing_required_field", occ=1),
        _reason("extract.missing_required_field", occ=1),
        _reason("extract.missing_required_field", occ=1),
    ]
    inserted = _materialize_review_reasons(
        sync_db, run_id=run_id, workspace_id=ws_id, stage_name="extract_baseline", reasons=reasons
    )
    sync_db.commit()
    rows = (
        sync_db.execute(select(ReviewReason).where(ReviewReason.pipeline_run_id == run_id))
        .scalars()
        .all()
    )
    assert inserted == 1
    assert len(rows) == 1
    assert rows[0].occurrence_count == 3


def test_idempotent_across_calls_accumulates_count(sync_db) -> None:
    ws_id, run_id = str(uuid.uuid4()), str(uuid.uuid4())
    _materialize(sync_db, run_id, ws_id, [_reason("domain.validation_conflict", occ=2)])
    _materialize(sync_db, run_id, ws_id, [_reason("domain.validation_conflict", occ=5)])
    rows = _rows(sync_db, run_id)
    assert len(rows) == 1
    assert rows[0].occurrence_count == 7


def test_distinct_codes_separate_rows(sync_db) -> None:
    ws_id, run_id = str(uuid.uuid4()), str(uuid.uuid4())
    reasons = [
        _reason("extract.missing_required_field"),
        _reason("domain.validation_conflict"),
    ]
    _materialize_review_reasons(
        sync_db, run_id=run_id, workspace_id=ws_id, stage_name="extract_baseline", reasons=reasons
    )
    sync_db.commit()
    assert _count(sync_db, run_id) == 2


def test_cap_limits_new_rows(sync_db) -> None:
    ws_id, run_id = str(uuid.uuid4()), str(uuid.uuid4())
    over_cap = _REVIEW_REASON_ROW_CAP + 10
    reasons = [_reason(f"synthetic.code_{i}") for i in range(over_cap)]
    inserted = _materialize_review_reasons(
        sync_db, run_id=run_id, workspace_id=ws_id, stage_name="extract_baseline", reasons=reasons
    )
    sync_db.commit()
    assert inserted == _REVIEW_REASON_ROW_CAP
    assert _count(sync_db, run_id) == _REVIEW_REASON_ROW_CAP


def test_empty_code_payload_skipped(sync_db) -> None:
    ws_id, run_id = str(uuid.uuid4()), str(uuid.uuid4())
    inserted = _materialize_review_reasons(
        sync_db,
        run_id=run_id,
        workspace_id=ws_id,
        stage_name="extract_baseline",
        reasons=[_reason(""), _reason("extract.low_confidence")],
    )
    sync_db.commit()
    assert inserted == 1
    assert _count(sync_db, run_id) == 1


def test_query_mae_uses_composite_index(sync_db) -> None:
    ws_id, run_id = str(uuid.uuid4()), str(uuid.uuid4())
    _materialize(sync_db, run_id, ws_id, [_reason("domain.validation_conflict", occ=4)])
    row = sync_db.execute(
        select(ReviewReason).where(
            ReviewReason.workspace_id == ws_id,
            ReviewReason.pipeline_run_id == run_id,
            ReviewReason.code == "domain.validation_conflict",
        )
    ).scalar_one()
    assert row.occurrence_count == 4
    plan = _explain_plan(sync_db, ws_id=ws_id, run_id=run_id, code="domain.validation_conflict")
    assert "ix_review_reasons_ws_run_code" in plan


def _needs_review_detail() -> dict:
    return {
        "validation": {
            "errors": ["E1.5: item sem code"],
            "issues": [{"code": "e15.item.empty_code", "severity": "warning"}],
            "review_reasons": [
                _reason("extract.missing_required_field", occ=2),
                _reason("extract.missing_required_field", occ=1),
            ],
        }
    }


def test_record_stage_needs_review_persists_reasons(sync_db) -> None:
    ws_id, run_id, log_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    _seed_run(sync_db, run_id=run_id, ws_id=ws_id, log_id=log_id)
    result = _FakeStageResult(detail=_needs_review_detail())
    with patch("backend.app.tasks.pipeline_task.publish_needs_review") as pub:
        _record_stage_needs_review(run_id, "extract_baseline", log_id, result, elapsed_ms=12)
    pub.assert_called_once_with(run_id, "extract_baseline")

    rows = _rows(sync_db, run_id)
    run = sync_db.get(PipelineRun, run_id)
    assert len(rows) == 1
    assert rows[0].code == "extract.missing_required_field"
    assert rows[0].occurrence_count == 3
    assert run.status == PipelineRunStatus.needs_review
