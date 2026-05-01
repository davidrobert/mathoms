#!/usr/bin/env python3
"""Tests for pipeline orchestrator — verifica importação, API pública,
e lógica de sequenciamento."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestPublicAPI:
    """Verifica que o package pipeline expõe a API pública correta."""

    def test_import_package(self):
        import pipeline

        assert hasattr(pipeline, "__version__")
        assert pipeline.__version__ == "0.2.0"

    def test_import_run_pipeline(self):
        from pipeline import run_pipeline

        assert callable(run_pipeline)

    def test_import_run_from(self):
        from pipeline import run_from

        assert callable(run_from)

    def test_import_run_stages(self):
        from pipeline import run_stages

        assert callable(run_stages)

    def test_import_workspace_context(self):
        from pipeline import WorkspaceContext

        assert callable(WorkspaceContext.default)
        assert callable(WorkspaceContext.for_tenant)

    def test_import_result_types(self):
        from pipeline import PipelineResult, StageResult

        pr = PipelineResult()
        assert pr.success is True
        assert pr.failed_stage is None

        sr = StageResult(stage="E5", success=True)
        assert sr.stage == "E5"


class TestOrchestratorLogic:
    """Verifica lógica de sequenciamento sem executar pipeline real."""

    def test_deterministic_order_excludes_llm(self):
        from pipeline.orchestrator import DETERMINISTIC_ORDER, LLM_STAGES

        for stage in DETERMINISTIC_ORDER:
            assert stage not in LLM_STAGES

    def test_full_order_includes_llm(self):
        from pipeline.orchestrator import FULL_ORDER, LLM_STAGES

        # LLM_STAGES contém aliases legados + descritivos (F9.2 compat) — só
        # exigimos que cada item de FULL_ORDER que é LLM esteja em LLM_STAGES.
        from pipeline.stage_spec import STAGE_REGISTRY

        for stage in FULL_ORDER:
            if STAGE_REGISTRY[stage].is_llm:
                assert stage in LLM_STAGES

    def test_from_map_e3_starts_at_e3(self):
        from pipeline.orchestrator import FROM_MAP

        # Legacy key continua funcionando, mas conteúdo é descritivo (F9.2).
        stages = FROM_MAP["E3"]
        assert stages[0] == "reconcile_transactions"
        assert "extract_members" not in stages
        assert "analyze_finances" in stages

    def test_from_map_e5_starts_at_e5(self):
        from pipeline.orchestrator import FROM_MAP

        stages = FROM_MAP["E5"]
        assert stages[0] == "analyze_finances"
        assert "reconcile_transactions" not in stages

    def test_from_map_invalid_returns_error(self):
        from pipeline import WorkspaceContext, run_from

        ctx = WorkspaceContext.default()
        result = run_from(ctx, "INVALID")
        assert not result.success
        assert result.failed_stage == "INVALID"

    def test_get_stage_runner_returns_callable_for_known(self):
        from pipeline.orchestrator import _get_stage_runner

        for stage in ["E3", "E4", "E5", "E5.N", "E7-crossval"]:
            runner = _get_stage_runner(stage)
            assert runner is not None, f"No runner for {stage}"
            assert callable(runner)

    def test_get_stage_runner_returns_callable_for_implemented_llm(self):
        from pipeline.orchestrator import _get_stage_runner

        for stage in ["E1", "E1.5", "E2-llm"]:
            runner = _get_stage_runner(stage)
            assert (
                runner is not None
            ), f"Runner should be callable for implemented LLM stage {stage}"
            assert callable(runner)

    def test_get_stage_runner_returns_callable_for_e7_review(self):
        from pipeline.orchestrator import _get_stage_runner

        runner = _get_stage_runner("E7-review")
        assert runner is not None, "E7-review should have a runner"
        assert callable(runner)

    def test_every_full_order_stage_has_runner(self):
        from pipeline.orchestrator import FULL_ORDER, _get_stage_runner

        missing = [s for s in FULL_ORDER if _get_stage_runner(s) is None]
        assert not missing, f"FULL_ORDER stages without runner: {missing}"

    def test_pipeline_result_summary(self):
        from pipeline import PipelineResult, StageResult

        pr = PipelineResult(
            stages=[
                StageResult(stage="E3", success=True, duration_ms=100),
                StageResult(stage="E4", success=True, duration_ms=200),
                StageResult(stage="E5", success=False, error="test error"),
            ]
        )
        s = pr.summary()
        assert s["success"] is False
        assert s["total_stages"] == 3
        assert s["passed"] == 2
        assert s["failed"] == 1
        assert s["failed_stage"] == "E5"

    def test_stages_list_consistency(self):
        """Verifica que FROM_MAP contém apenas stages válidos do FULL_ORDER."""
        from pipeline.orchestrator import FROM_MAP, FULL_ORDER

        valid = set(FULL_ORDER)
        for key, stages in FROM_MAP.items():
            for s in stages:
                assert s in valid, f"FROM_MAP['{key}'] has invalid stage '{s}'"

    def test_run_stage_maps_success_false_from_detail_dict(self, monkeypatch, tmp_path):
        """E2-llm (e similares) retornam dict com success=False sem exceção — o orquestrador deve falhar a etapa."""
        from pipeline import orchestrator
        from pipeline.context import WorkspaceContext

        def fake_get_runner(stage: str):
            if stage != "E2-llm":
                return None

            def run(ctx):
                return {"success": False, "errors": [{"file": "x.pdf"}], "total_errors": 1}

            return run

        monkeypatch.setattr(orchestrator, "_get_stage_runner", fake_get_runner)
        ctx = WorkspaceContext(root=tmp_path)
        sr = orchestrator._run_stage(ctx, "E2-llm")
        assert sr.success is False
        assert sr.detail["total_errors"] == 1
