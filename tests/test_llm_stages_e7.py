#!/usr/bin/env python3
"""E7-review LLM stage runner + output converter tests.

All tests mock LLM calls — no real API keys needed.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._llm_stage_fixtures import (
    make_e7_review_output,
    make_llm_call_result,
    make_llm_ctx,
    make_llm_ctx_no_llm,
)


# ══════════════════════════════════════════════════════════════════════════
# E7-REVIEW STAGE RUNNER
# ══════════════════════════════════════════════════════════════════════════


class TestE7ReviewStage:
    def test_skips_without_llm_config(self, tmp_path):
        ctx = make_llm_ctx_no_llm(tmp_path)
        from pipeline.stages.e7_review_llm import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "free tier" in result["reason"]

    def test_skips_without_e5_analysis(self, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        from pipeline.stages.e7_review_llm import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "E5" in result["reason"]

    @patch("pipeline.llm.litellm_client.LLMService.call")
    @patch("pipeline.llm.litellm_client.LLMService._ensure_client")
    def test_runs_successfully_with_mock(self, mock_ensure, mock_call, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        ctx.e5_dir.mkdir(parents=True)
        (ctx.e5_dir / "analise_financeira-5_analysis.json").write_text(
            json.dumps({"score": 70, "patrimonio_liquido": 897000})
        )

        mock_call.return_value = make_llm_call_result(make_e7_review_output())

        from pipeline.stages.e7_review_llm import run
        result = run(ctx)

        assert result["success"] is True
        assert result["insights_count"] == 1
        assert result["recommendations_count"] == 1
        assert result["risk_level"] == "moderate"
        assert result["confidence"] == 0.85

        out_path = ctx.e7_dir / "review_llm-7_review.json"
        assert out_path.exists()

        data = json.loads(out_path.read_text())
        assert data["nivel_risco"] == "moderate"
        assert len(data["insights"]) == 1
        assert "resumo_executivo" in data["narrativas"]


class TestE7ReviewOutputConverter:
    def test_output_to_review_json(self):
        from pipeline.stages.e7_review_llm import _output_to_review_json
        output = make_e7_review_output()
        result = _output_to_review_json(output)

        assert result["nivel_risco"] == "moderate"
        assert result["avaliacao_geral"] == "Saúde financeira moderada."
        assert len(result["insights"]) == 1
        assert result["insights"][0]["categoria"] == "patrimonio"
        assert len(result["ajustes_score"]) == 1
        assert result["ajustes_score"][0]["ajuste"] == -10.0
        assert "resumo_executivo" in result["narrativas"]
        assert result["_meta"]["source"] == "E7-review-llm"
