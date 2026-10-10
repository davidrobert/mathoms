"""Paridade de hidratação HTTP ↔ Celery (ADR-303 §Escopo deferido, fechado).

O executor HTTP passa a hidratar o ``WorkspaceContext`` via
``run_context_factory`` — mesmo factory do Celery. Sem estes asserts, a
regressão volta muda (stage roda com config de disco em silêncio).

A coexistência das DUAS sessões por stage (config read-only + artifact
read-write, invariante ADR-256) é exercitada com escrita real em
``test_artifact_store_integration.py`` — aqui o alvo é o shape do ctx.
"""

from __future__ import annotations

from pathlib import Path


def _assert_fully_hydrated(ctx) -> None:
    assert ctx.config_store is not None
    assert ctx.property_identity_resolver is not None
    assert ctx.economic_assumptions_resolver is not None
    assert ctx.property_overrides_resolver is not None
    assert ctx.llm_call_hooks is not None, "budget hard-stop ADR-173 no modo HTTP"
    assert ctx.artifact_store is not None


def test_http_stage_context_is_hydrated(client, tmp_path: Path, monkeypatch):
    import pipeline.orchestrator as orch
    from pipeline.orchestrator import StageResult

    captured: dict = {}

    def spy_run_stage(ctx, stage):
        captured["ctx"] = ctx
        return StageResult(stage=stage, success=True)

    monkeypatch.setattr(orch, "_run_stage", spy_run_stage)

    r = client.post(
        "/api/v1/pipeline/stages/reconcile_transactions/execute",
        json={"run_id": "run-hyd", "workspace_id": "ws-hyd", "workspace_root": str(tmp_path)},
    )

    assert r.status_code == 200, r.text
    ctx = captured["ctx"]
    _assert_fully_hydrated(ctx)
    assert (ctx.workspace_id, ctx.pipeline_run_id) == ("ws-hyd", "run-hyd")


def test_http_stage_context_carries_base_run_pin(client, tmp_path: Path, monkeypatch):
    """ADR-291: o ctx remoto diz o mesmo pin que o store — paridade com o ctx do Celery."""
    import pipeline.orchestrator as orch
    from pipeline.orchestrator import StageResult

    captured: dict = {}

    def spy_run_stage(ctx, stage):
        captured["ctx"] = ctx
        return StageResult(stage=stage, success=True)

    monkeypatch.setattr(orch, "_run_stage", spy_run_stage)

    r = client.post(
        "/api/v1/pipeline/stages/categorize_transactions/execute",
        json={
            "run_id": "run-cauda",
            "workspace_id": "ws-hyd",
            "workspace_root": str(tmp_path),
            "base_run_id": "run-base",
            "base_run_fallback_stages": ["E3", "reconcile_transactions"],
        },
    )

    assert r.status_code == 200, r.text
    ctx = captured["ctx"]
    assert ctx.base_run_id == "run-base"
    assert ctx.base_run_fallback_stages == frozenset({"E3", "reconcile_transactions"})


def test_hydration_failure_maps_to_503(client, tmp_path: Path, monkeypatch):
    from backend.app.services.pipeline import run_context_factory

    def _boom(**kwargs):
        raise RuntimeError("config DB down")

    monkeypatch.setattr(run_context_factory, "build_hydrated_context", _boom)

    r = client.post(
        "/api/v1/pipeline/stages/reconcile_transactions/execute",
        json={"run_id": "r", "workspace_id": "w", "workspace_root": str(tmp_path)},
    )
    assert r.status_code == 503
    assert "ADR-303" in r.json()["detail"]
