"""A33.l5 (ADR-307 F2) — drift nightly do extract_with_llm.

CI de PR nunca chama Anthropic: todos os caminhos usam
``tests.fakes.llm.FakeSequenceLLMClient`` ou testam o skip sem key.
"""

from __future__ import annotations

import logging

import pytest
from celery.schedules import crontab
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.core.database import Base
from backend.app.models.llm_drift_check import LLMDriftCheck
from backend.app.services.extract_llm_drift import (
    DRIFT_STAGE,
    evaluate_structural,
    persist_drift_results,
    run_extract_llm_drift,
)
from backend.app.services.extract_llm_drift_fixtures import (
    EXTRACT_LLM_DRIFT_FIXTURES,
    StructuralExpectation,
)
from backend.app.tasks.detect_extract_llm_drift import (
    _execute_drift_check,
    detect_extract_llm_drift,
)
from backend.app.worker import celery_app
from pipeline.llm.call_hooks import LLMBudgetExceededError
from pipeline.llm.prompts.e2_llm import PROMPT_VERSION
from pipeline.llm.schemas.e2_llm_extract import (
    ExtractedInvestment,
    ExtractedTransaction,
    LLMExtractOutput,
)
from tests.fakes.fake_llm_client import FakeSequenceLLMClient

# ────────────────────────────── helpers ──────────────────────────────


def _tx(date: str = "2026-03-05", amount: float = -100.0) -> ExtractedTransaction:
    return ExtractedTransaction(date=date, description="TX SINTETICA", amount=amount)


def _inv(applied_date: str | None = "2025-01-10") -> ExtractedInvestment:
    return ExtractedInvestment(
        type="cdb",
        institution="btgpactual",
        description="CDB SINTETICO",
        value_brl=25000.0,
        applied_date=applied_date,
    )


def _output(**overrides) -> LLMExtractOutput:
    base = dict(
        source_file="sintetico.pdf",
        institution="c6bank",
        document_type="extrato",
        currency="BRL",
        transactions=[],
        investments=[],
        confidence=0.95,
    )
    base.update(overrides)
    return LLMExtractOutput(**base)


def _conforming_outputs() -> list[LLMExtractOutput]:
    """1 output válido por fixture, na ordem de EXTRACT_LLM_DRIFT_FIXTURES."""
    return [
        _output(institution="c6bank", transactions=[_tx() for _ in range(5)]),
        _output(institution="btgpactual", investments=[_inv() for _ in range(3)]),
        _output(institution="itau", document_type="informe_rendimentos"),
        _output(institution="globalbank", currency="USD", transactions=[_tx(), _tx()]),
    ]


@pytest.fixture
def drift_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield lambda: Session(engine)
    engine.dispose()


# ───────────────────────── beat schedule / registro ─────────────────────────


def test_beat_schedule_has_nightly_drift_entry():
    entry = celery_app.conf.beat_schedule["detect-extract-llm-drift"]
    assert entry["task"] == "fin.llm.detect_extract_llm_drift"
    schedule = entry["schedule"]
    assert isinstance(schedule, crontab)
    assert schedule.hour == {6}
    assert schedule.minute == {15}


def test_task_registered_and_included():
    assert "fin.llm.detect_extract_llm_drift" in celery_app.tasks
    assert "backend.app.tasks.detect_extract_llm_drift" in celery_app.conf.include


# ───────────────────────── evaluate_structural ─────────────────────────


def test_evaluate_structural_conforming_output_passes():
    expect = StructuralExpectation(
        institution="c6bank", currency="BRL", min_transactions=3, max_transactions=7
    )
    output = _output(transactions=[_tx() for _ in range(5)])
    assert evaluate_structural(output, expect) == []


def test_evaluate_structural_institution_mismatch_names_offender():
    expect = StructuralExpectation(institution="c6bank")
    failures = evaluate_structural(_output(institution="nubank"), expect)
    assert failures == ["institution: expected 'c6bank', got 'nubank'"]


def test_evaluate_structural_empty_institution_fails():
    failures = evaluate_structural(_output(institution="  "), StructuralExpectation())
    assert any("non-empty" in f for f in failures)


def test_evaluate_structural_phantom_transactions_in_informe():
    expect = StructuralExpectation(institution="itau", max_transactions=0)
    output = _output(institution="itau", transactions=[_tx() for _ in range(3)])
    failures = evaluate_structural(output, expect)
    assert "transactions: expected <= 0, got 3" in failures


def test_evaluate_structural_date_shape_drift():
    expect = StructuralExpectation(institution="c6bank")
    output = _output(transactions=[_tx(date="05/03/2026")])
    failures = evaluate_structural(output, expect)
    assert failures == ["transactions[0].date: expected YYYY-MM-DD, got '05/03/2026'"]


def test_evaluate_structural_investment_date_shape_drift():
    expect = StructuralExpectation(institution="btgpactual", min_investments=1)
    output = _output(institution="btgpactual", investments=[_inv(applied_date="10/01/2025")])
    failures = evaluate_structural(output, expect)
    assert failures == [
        "investments[0].applied_date: expected YYYY-MM-DD or null, got '10/01/2025'"
    ]


# ───────────────────────── run_extract_llm_drift ─────────────────────────


def test_run_one_trial_per_fixture_all_pass():
    fake = FakeSequenceLLMClient(outputs=list(_conforming_outputs()))
    results = run_extract_llm_drift(fake)
    assert fake.calls == len(EXTRACT_LLM_DRIFT_FIXTURES)
    assert [r.passed for r in results] == [True, True, True, True]
    assert {k["stage"] for k in fake.seen_kwargs} == {DRIFT_STAGE}
    assert {k["prompt_version"] for k in fake.seen_kwargs} == {PROMPT_VERSION}


def test_run_call_failure_is_recorded_and_batch_continues():
    outputs = _conforming_outputs()
    outputs[1] = RuntimeError("provider 500")
    fake = FakeSequenceLLMClient(outputs=outputs)
    results = run_extract_llm_drift(fake)
    assert fake.calls == 4
    assert results[1].passed is False
    assert results[1].failures[0].startswith("llm_call_failed: RuntimeError")
    assert [r.passed for r in results] == [True, False, True, True]


def test_run_budget_hard_stop_short_circuits_remaining_fixtures():
    from decimal import Decimal

    exc = LLMBudgetExceededError("ws-1", Decimal("22"), Decimal("20"))
    fake = FakeSequenceLLMClient(outputs=[exc])
    results = run_extract_llm_drift(fake)
    assert fake.calls == 1
    assert all(not r.passed for r in results)
    assert all("budget_exceeded" in r.failures[0] for r in results)


# ───────────────────────── persistência consultável ─────────────────────────


def test_persist_drift_results_rows_consultaveis(drift_session_factory):
    fake = FakeSequenceLLMClient(outputs=list(_conforming_outputs()))
    results = run_extract_llm_drift(fake)
    batch_id = persist_drift_results(
        results, model_name="fake-llm", session_factory=drift_session_factory
    )

    with drift_session_factory() as db:
        rows = db.execute(select(LLMDriftCheck).order_by(LLMDriftCheck.fixture_id)).scalars().all()
    assert len(rows) == 4
    assert {r.batch_id for r in rows} == {batch_id}
    assert {r.stage for r in rows} == {DRIFT_STAGE}
    assert all(r.passed and r.failures is None and r.created_at is not None for r in rows)
    assert {r.prompt_version for r in rows} == {PROMPT_VERSION}


def test_persist_drift_results_keeps_failure_messages(drift_session_factory):
    outputs = _conforming_outputs()
    outputs[0] = _output(institution="nubank", transactions=[_tx() for _ in range(5)])
    fake = FakeSequenceLLMClient(outputs=outputs)
    persist_drift_results(
        run_extract_llm_drift(fake),
        model_name="fake-llm",
        session_factory=drift_session_factory,
    )

    with drift_session_factory() as db:
        failed = (
            db.execute(select(LLMDriftCheck).where(LLMDriftCheck.passed.is_(False))).scalars().all()
        )
    assert len(failed) == 1
    assert failed[0].fixture_id == "extrato_c6bank_brl"
    assert failed[0].failures == ["institution: expected 'c6bank', got 'nubank'"]


# ───────────────────────── corpo do task + telemetria ─────────────────────────


def test_execute_drift_check_emits_error_metric_on_failure(drift_session_factory, caplog):
    outputs = _conforming_outputs()
    outputs[2] = _output(institution="itau", transactions=[_tx()])  # informe com tx fantasma
    fake = FakeSequenceLLMClient(outputs=outputs)

    with caplog.at_level(logging.INFO, logger="mathoms.llm.drift"):
        summary = _execute_drift_check(
            fake, model_name="fake-llm", session_factory=drift_session_factory
        )

    assert summary["fixtures"] == 4
    assert summary["failed"] == 1
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1
    assert errors[0].name == "mathoms.llm.drift"
    assert errors[0].fixture_id == "informe_rendimentos_itau"
    assert errors[0].failures == ["transactions: expected <= 0, got 1"]
    completed = [r for r in caplog.records if "completed" in r.getMessage()]
    assert completed and completed[0].batch_id == summary["batch_id"]


def test_execute_drift_check_all_pass_no_error_log(drift_session_factory, caplog):
    fake = FakeSequenceLLMClient(outputs=list(_conforming_outputs()))
    with caplog.at_level(logging.INFO, logger="mathoms.llm.drift"):
        summary = _execute_drift_check(
            fake, model_name="fake-llm", session_factory=drift_session_factory
        )
    assert summary["passed"] == 4
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_task_skips_without_api_key(monkeypatch, caplog):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with caplog.at_level(logging.ERROR, logger="mathoms.llm.drift"):
        result = detect_extract_llm_drift.apply().get()
    assert result == {"skipped": True, "reason": "ANTHROPIC_API_KEY missing"}
    assert any("ANTHROPIC_API_KEY missing" in r.getMessage() for r in caplog.records)
