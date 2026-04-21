"""Stage-level execution tests.

Uses monkeypatching of `pipeline.orchestrator._run_stage` to avoid touching
real workspace artefacts — the executor is a thin wrapper, so the valuable
check is contract translation, not stage logic.
"""

from __future__ import annotations

from pathlib import Path


def test_unknown_stage_returns_404(client, tmp_path):
    r = client.post(
        "/api/v1/pipeline/stages/ZZ-bogus/execute",
        json={
            "run_id": "r1",
            "workspace_id": "ws1",
            "workspace_root": str(tmp_path),
        },
    )
    assert r.status_code == 404
    assert "unknown stage" in r.json()["detail"]


def test_stage_executor_delegates_to_orchestrator(client, tmp_path, monkeypatch):
    """Happy-path: executor hands the context to orchestrator and echoes StageResult."""
    captured: dict = {}

    def fake_run_stage(ctx, stage):
        from pipeline.orchestrator import StageResult
        captured["stage"] = stage
        captured["root"] = ctx.root
        captured["run_id"] = ctx.pipeline_run_id
        captured["incremental"] = ctx.incremental
        return StageResult(
            stage=stage, success=True, duration_ms=42.0,
            detail={"processed": 3},
        )

    import pipeline.orchestrator as orch
    monkeypatch.setattr(orch, "_run_stage", fake_run_stage)
    # Router imports the symbol lazily; patch the already-imported copy too.
    import app.services.stage_executor as se_mod
    monkeypatch.setattr(
        "pipeline.orchestrator._run_stage", fake_run_stage, raising=True
    )

    r = client.post(
        "/api/v1/pipeline/stages/E3/execute",
        json={
            "run_id": "run-abc",
            "workspace_id": "ws-xyz",
            "workspace_root": str(tmp_path),
            "incremental": True,
            "incremental_doc_paths": ["doc-1"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "stage": "E3",
        "success": True,
        "duration_ms": 42.0,
        "detail": {"processed": 3},
        "error": None,
        "attempts": 1,
    }
    assert captured["stage"] == "E3"
    assert Path(captured["root"]).resolve() == tmp_path.resolve()
    assert captured["run_id"] == "run-abc"
    assert captured["incremental"] is True


def test_stage_executor_propagates_failure(client, tmp_path, monkeypatch):
    def failing(ctx, stage):
        from pipeline.orchestrator import StageResult
        return StageResult(stage=stage, success=False, error="boom")

    monkeypatch.setattr("pipeline.orchestrator._run_stage", failing, raising=True)

    r = client.post(
        "/api/v1/pipeline/stages/E4/execute",
        json={
            "run_id": "r1",
            "workspace_id": "ws1",
            "workspace_root": str(tmp_path),
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is False
    assert body["error"] == "boom"
