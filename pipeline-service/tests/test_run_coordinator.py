"""Run-coordinator tests — multi-stage sequencing with mocked orchestrator."""

from __future__ import annotations

import contextlib
from types import SimpleNamespace

import pytest


def test_run_rejects_unknown_stage(client, tmp_path):
    r = client.post(
        "/api/v1/pipeline/runs",
        json={
            "run_id": "r1",
            "workspace_id": "ws1",
            "workspace_root": str(tmp_path),
            "stages": ["E3", "bogus"],
        },
    )
    assert r.status_code == 400
    assert "unknown stage" in r.json()["detail"]


def test_run_sequences_stages_and_aggregates(client, tmp_path, monkeypatch):
    calls: list[str] = []

    def fake_run_stage(ctx, stage):
        from pipeline.orchestrator import StageResult

        calls.append(stage)
        return StageResult(stage=stage, success=True, duration_ms=1.0)

    monkeypatch.setattr("pipeline.orchestrator._run_stage", fake_run_stage, raising=True)

    r = client.post(
        "/api/v1/pipeline/runs",
        json={
            "run_id": "r1",
            "workspace_id": "ws1",
            "workspace_root": str(tmp_path),
            "stages": ["E3", "E4", "E5"],
            "skip_llm": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["failed_stage"] is None
    # Boundary resolve legacy → descritivo (ADR-093); executor e echo
    # trabalham sempre com o nome canônico.
    expected = ["reconcile_transactions", "categorize_transactions", "analyze_finances"]
    assert [s["stage"] for s in body["stages"]] == expected
    assert calls == expected


def test_run_stops_on_error_by_default(client, tmp_path, monkeypatch):
    def fake_run_stage(ctx, stage):
        from pipeline.orchestrator import StageResult

        ok = stage != "categorize_transactions"
        return StageResult(stage=stage, success=ok, error=None if ok else "x")

    monkeypatch.setattr("pipeline.orchestrator._run_stage", fake_run_stage, raising=True)

    r = client.post(
        "/api/v1/pipeline/runs",
        json={
            "run_id": "r1",
            "workspace_id": "ws1",
            "workspace_root": str(tmp_path),
            "stages": ["reconcile_transactions", "categorize_transactions", "analyze_finances"],
        },
    )
    body = r.json()
    assert body["success"] is False
    assert body["failed_stage"] == "categorize_transactions"
    # stop_on_error=True (default) → analyze_finances not attempted
    assert [s["stage"] for s in body["stages"]] == [
        "reconcile_transactions",
        "categorize_transactions",
    ]


def test_run_skips_llm_stages_when_requested(client, tmp_path, monkeypatch):
    executed: list[str] = []

    def fake_run_stage(ctx, stage):
        from pipeline.orchestrator import StageResult

        executed.append(stage)
        return StageResult(stage=stage, success=True)

    monkeypatch.setattr("pipeline.orchestrator._run_stage", fake_run_stage, raising=True)

    r = client.post(
        "/api/v1/pipeline/runs",
        json={
            "run_id": "r1",
            "workspace_id": "ws1",
            "workspace_root": str(tmp_path),
            "stages": ["extract_members", "reconcile_transactions"],  # extract_members is LLM
            "skip_llm": True,
        },
    )
    body = r.json()
    assert body["success"] is True
    # LLM stage never reaches orchestrator
    assert executed == ["reconcile_transactions"]
    stages_resp = {s["stage"]: s for s in body["stages"]}
    assert stages_resp["extract_members"]["detail"]["skipped"] is True


class _FlushRecorder:
    """Hooks fake: anota se a transação do stage ainda estava aberta quando o flush veio."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self.flushes_inside_stage_transaction: list[bool] = []

    def flush_call_log(self) -> None:
        session = self._ctx.artifact_store.session
        self.flushes_inside_stage_transaction.append(session.in_transaction())


@pytest.mark.parametrize("stage_raises", [False, True])
def test_deferred_call_log_flushes_after_the_stage_session_closes(
    tmp_path, monkeypatch, stage_raises
):
    """Em SQLite o LLMCallLog só grava com o write-lock do stage liberado (ADR-173 §Emenda 2026-10-08)."""
    from app.contracts.runs import RunStartRequest
    from app.services.run_coordinator import _execute_one_stage

    from pipeline.orchestrator import StageResult

    def fake_run_stage(ctx, stage):
        ctx.artifact_store.write("llm_lock_probe", "doc-0", {"idx": 0})
        if stage_raises:
            raise RuntimeError("fixture: falha deterministica")
        return StageResult(stage=stage, success=True, duration_ms=1.0)

    monkeypatch.setattr("pipeline.orchestrator._run_stage", fake_run_stage, raising=True)
    ctx = SimpleNamespace(artifact_store=None)
    ctx.llm_call_hooks = _FlushRecorder(ctx)
    req = RunStartRequest(
        run_id="r1", workspace_id="ws1", workspace_root=str(tmp_path), stages=["E1.5"]
    )

    with contextlib.suppress(RuntimeError):
        _execute_one_stage(req, ctx, "extract_baseline")

    assert ctx.llm_call_hooks.flushes_inside_stage_transaction == [False]
