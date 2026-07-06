"""Tests Fase 2 (ADR-272) — adapter materializa review_reasons em DB real (SQLite via SyncSessionLocal, nunca mock): consolidação 1-por-(run,code), occurrence_count agregado, cap e query-mãe."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from backend.app.core.database import SyncSessionLocal
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


@pytest_asyncio.fixture
async def sync_db(db):
    # Depender de `db` (async) força o autouse `setup_db` a criar o schema no
    # arquivo SQLite compartilhado. Usamos `SyncSessionLocal` (mesma factory que
    # o código de produção sob teste abre internamente), não `_sync_test_engine`
    # da conftest — esse usa StaticPool e mantém uma conexão com snapshot vazio
    # do schema, enxergando 0 tabelas (drift conhecido). `SyncSessionLocal`
    # abre conexão nova por sessão e vê o DDL recém-criado.
    with SyncSessionLocal() as session:
        yield session


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


@pytest.mark.asyncio
async def test_consolidates_same_code_to_single_row(sync_db) -> None:
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


@pytest.mark.asyncio
async def test_idempotent_across_calls_accumulates_count(sync_db) -> None:
    ws_id, run_id = str(uuid.uuid4()), str(uuid.uuid4())
    _materialize(sync_db, run_id, ws_id, [_reason("domain.validation_conflict", occ=2)])
    _materialize(sync_db, run_id, ws_id, [_reason("domain.validation_conflict", occ=5)])
    rows = _rows(sync_db, run_id)
    assert len(rows) == 1
    assert rows[0].occurrence_count == 7


@pytest.mark.asyncio
async def test_distinct_codes_separate_rows(sync_db) -> None:
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


@pytest.mark.asyncio
async def test_cap_limits_new_rows(sync_db) -> None:
    ws_id, run_id = str(uuid.uuid4()), str(uuid.uuid4())
    over_cap = _REVIEW_REASON_ROW_CAP + 10
    reasons = [_reason(f"synthetic.code_{i}") for i in range(over_cap)]
    inserted = _materialize_review_reasons(
        sync_db, run_id=run_id, workspace_id=ws_id, stage_name="extract_baseline", reasons=reasons
    )
    sync_db.commit()
    assert inserted == _REVIEW_REASON_ROW_CAP
    assert _count(sync_db, run_id) == _REVIEW_REASON_ROW_CAP


@pytest.mark.asyncio
async def test_empty_code_payload_skipped(sync_db) -> None:
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


@pytest.mark.asyncio
async def test_query_mae_uses_composite_index(sync_db) -> None:
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


@pytest.mark.asyncio
async def test_record_stage_needs_review_persists_reasons(sync_db) -> None:
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


def test_has_validation_errors_covers_deterministic_e3_shape() -> None:
    """A28.l8: gate needs_review deixou de exigir is_llm — o contrato passa a ser
    só o bloco validation do detail (E3 emite valid=False p/ período implausível
    / banco vazio; stage sem bloco validation nunca pausa)."""
    from backend.app.tasks.pipeline_task import _has_validation_errors

    e3_detail = {
        "files_created": [],
        "validation": {"valid": False, "errors": ["periodo implausivel"], "review_reasons": []},
    }
    assert _has_validation_errors(_FakeStageResult(detail=e3_detail)) is True
    assert _has_validation_errors(_FakeStageResult(detail={"files_created": []})) is False
    assert _has_validation_errors(_FakeStageResult(detail={"validation": {"valid": True}})) is False


# ── A29.l2 (ADR-308): projeção ReviewReason → validation_issues ────────────


def _issues_helpers():
    from backend.app.tasks.pipeline_task import (
        _ISSUE_CAP_PER_CODE,
        _issues_from_reasons,
        _resolve_document_ids,
    )

    return _ISSUE_CAP_PER_CODE, _issues_from_reasons, _resolve_document_ids


def test_issues_from_reasons_severity_and_order() -> None:
    _, _issues_from_reasons, _ = _issues_helpers()
    reasons = [
        _reason("domain.balance_gap"),
        _reason("domain.balance_gap"),
        _reason("extract.missing_required_field"),
    ]
    issues = _issues_from_reasons(reasons, {})
    # Blocking primeiro (error), depois domain.* (warning), maior grupo primeiro.
    assert issues[0]["code"] == "extract.missing_required_field"
    assert issues[0]["severity"] == "error"
    assert issues[1]["code"] == "domain.balance_gap"
    assert issues[1]["severity"] == "warning"
    assert issues[0]["context"]["artifact_key"] == "irpfdeclaracao_2024"
    assert issues[0]["legacy_message"] == "y"


def test_issues_from_reasons_cap_with_sentinel() -> None:
    cap, _issues_from_reasons, _ = _issues_helpers()
    reasons = [_reason("dedup.sentinel_period") for _ in range(cap + 15)]
    issues = _issues_from_reasons(reasons, {})
    assert len(issues) == cap + 1
    sentinel = issues[-1]
    assert sentinel["context"] == {"truncated": True, "remaining": 15}
    assert "15" in sentinel["legacy_message"]


def _seed_document(db, ws_id: str, hash_prefix: str):
    from backend.app.models.document import Document, DocumentStatus, DocumentType

    doc = Document(
        workspace_id=ws_id,
        original_name="extrato.pdf",
        stored_path="/tmp/x.pdf",
        doc_type=DocumentType.bank_statement,
        status=DocumentStatus.ready,
        content_hash=hash_prefix + "0" * 52,
    )
    db.add(doc)
    db.commit()
    return doc


@pytest.mark.asyncio
async def test_resolve_document_ids_by_hash_prefix(sync_db) -> None:
    _, _, _resolve_document_ids = _issues_helpers()
    ws_id = str(uuid.uuid4())
    doc = _seed_document(sync_db, ws_id, "f861374a39e9")
    keys = {
        "f861374a39e9_c6bank_extratoconta_202604_202604",
        "sem_prefixo_hash",
        "itau_BRL_baseline_2024",
    }
    resolved = _resolve_document_ids(sync_db, ws_id, keys)
    assert resolved == {"f861374a39e9_c6bank_extratoconta_202604_202604": doc.id}


def _fetch_review(db, run_id: str):
    from backend.app.models.stage_review import StageReview

    return db.execute(select(StageReview).where(StageReview.pipeline_run_id == run_id)).scalar_one()


def _record(run_id: str, log_id: str, detail: dict, stage: str = "reconcile_transactions") -> None:
    with patch("backend.app.tasks.pipeline_task.publish_needs_review"):
        _record_stage_needs_review(
            run_id, stage, log_id, _FakeStageResult(detail=detail), elapsed_ms=5
        )


def _e3_reasons_detail() -> dict:
    return {
        "validation": {
            "valid": False,
            "errors": ["extrato sem banco determinavel; documento requer revisao"],
            "review_reasons": [
                _reason(
                    "extract.missing_required_field",
                    artifact_key="abc123def456_itau_extratoconta_202601",
                ),
                _reason("domain.balance_gap", artifact_key="outro_sem_hash"),
            ],
        }
    }


@pytest.mark.asyncio
async def test_record_stage_needs_review_projects_validation_issues(sync_db) -> None:
    """ADR-272 crit. 6: sem validation.issues, StageReview.validation_issues
    é projetado das mesmas review_reasons — com document_id resolvido por hash."""
    ws_id, run_id, log_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    _seed_run(sync_db, run_id=run_id, ws_id=ws_id, log_id=log_id)
    doc = _seed_document(sync_db, ws_id, "abc123def456")
    _record(run_id, log_id, _e3_reasons_detail())
    issues = _fetch_review(sync_db, run_id).validation_issues
    assert issues is not None and len(issues) == 2
    assert issues[0]["code"] == "extract.missing_required_field"
    assert issues[0]["severity"] == "error"
    assert issues[0]["context"]["document_id"] == doc.id
    assert issues[1]["severity"] == "warning"
    assert issues[1]["context"]["document_id"] is None


@pytest.mark.asyncio
async def test_record_stage_keeps_native_issues_untouched(sync_db) -> None:
    """Stage LLM que já emite validation.issues (ADR-165) não é sobrescrito."""
    ws_id, run_id, log_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    _seed_run(sync_db, run_id=run_id, ws_id=ws_id, log_id=log_id)
    _record(run_id, log_id, _needs_review_detail(), stage="extract_baseline")
    issues = _fetch_review(sync_db, run_id).validation_issues
    assert issues == [{"code": "e15.item.empty_code", "severity": "warning"}]
