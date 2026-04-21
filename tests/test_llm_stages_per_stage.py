#!/usr/bin/env python3
"""Stage runner tests for E1, E1.5, E2-llm (sem E7 — ver `test_llm_stages_e7.py`).

All tests mock LLM calls — no real API keys needed.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._llm_stage_fixtures import (
    make_e15_output,
    make_e1_output,
    make_e2_llm_output,
    make_llm_call_result,
    make_llm_ctx,
    make_llm_ctx_no_llm,
)


# ══════════════════════════════════════════════════════════════════════════
# E1 STAGE RUNNER
# ══════════════════════════════════════════════════════════════════════════


class TestE1Stage:
    def test_skips_without_llm_config(self, tmp_path):
        ctx = make_llm_ctx_no_llm(tmp_path)
        from pipeline.stages.e1 import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "free tier" in result["reason"]

    def test_skips_without_documents(self, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        from pipeline.stages.e1 import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "No personal documents" in result["reason"]

    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.service.LLMService.call")
    @patch("pipeline.llm.service.LLMService._ensure_client")
    def test_runs_successfully_with_mock(self, mock_ensure, mock_call, mock_extract, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        (tmp_path / "data" / "income_tax_br").mkdir(parents=True)
        (tmp_path / "data" / "income_tax_br" / "irpf_2024.pdf").write_text("fake pdf content")

        mock_extract.return_value = "IRPF 2024 content here"
        mock_call.return_value = make_llm_call_result(make_e1_output())

        from pipeline.stages.e1 import run
        result = run(ctx)

        assert result["success"] is True
        assert result["members_extracted"] == 2
        assert result["confidence"] == 0.95
        assert result["tokens"]["in"] == 1500
        assert result["validation"]["valid"] is True

        out_path = ctx.members_dir / "members-1b_unified.json"
        assert out_path.exists()

        data = json.loads(out_path.read_text())
        assert "david" in data["membros"]
        assert "mariana" in data["membros"]
        assert data["titular"] == "david"

    def test_find_personal_docs(self, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        (tmp_path / "data" / "income_tax_br").mkdir(parents=True)
        (tmp_path / "data" / "income_tax_br" / "irpf.pdf").write_text("x")
        (tmp_path / "data" / "income_tax_br" / "readme.md").write_text("x")  # .md not in initial search
        (tmp_path / "data" / "income_tax_br" / "image.png").write_text("x")  # not matching

        from pipeline.stages.e1 import _find_personal_docs
        docs = _find_personal_docs(ctx)
        names = {d.name for d in docs}
        assert "irpf.pdf" in names
        assert "image.png" not in names


# ══════════════════════════════════════════════════════════════════════════
# E1.5 STAGE RUNNER
# ══════════════════════════════════════════════════════════════════════════


class TestE15Stage:
    def test_skips_without_llm_config(self, tmp_path):
        ctx = make_llm_ctx_no_llm(tmp_path)
        from pipeline.stages.e15 import run
        result = run(ctx)
        assert result["skipped"] is True

    def test_skips_without_documents(self, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        from pipeline.stages.e15 import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "No IRPF" in result["reason"]

    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.service.LLMService.call")
    @patch("pipeline.llm.service.LLMService._ensure_client")
    def test_runs_successfully_with_mock(self, mock_ensure, mock_call, mock_extract, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        (tmp_path / "data" / "income_tax_br").mkdir(parents=True)
        (tmp_path / "data" / "income_tax_br" / "irpf_2024.pdf").write_text("fake content")

        mock_extract.return_value = "IRPF data here"
        mock_call.return_value = make_llm_call_result(make_e15_output())

        from pipeline.stages.e15 import run
        result = run(ctx)

        assert result["success"] is True
        assert result["items_extracted"] == 2
        assert result["net_worth_brl"] == 550000.00
        assert result["validation"]["valid"] is True

        # A6a: E1.5 agora escreve via store → baseline_patrimonial-1.5_baseline.json
        # E1.5c lerá esse artefato e produzirá baseline_patrimonial-1.5_consolidated.json.
        out_path = ctx.e2_dir / "baseline_patrimonial-1.5_baseline.json"
        assert out_path.exists(), (
            f"E1.5 deveria ter escrito via store no path {out_path} — "
            "verificar que store.write('E1.5', 'baseline_patrimonial', ...) foi chamado."
        )

        data = json.loads(out_path.read_text())
        assert data["resumo"]["patrimonio_liquido"] == 550000.00
        assert len(data["itens"]) == 2


# ══════════════════════════════════════════════════════════════════════════
# E2-LLM STAGE RUNNER
# ══════════════════════════════════════════════════════════════════════════


class TestE2LLMStage:
    def test_skips_without_llm_config(self, tmp_path):
        ctx = make_llm_ctx_no_llm(tmp_path)
        from pipeline.stages.e2_llm import run
        result = run(ctx)
        assert result["skipped"] is True

    def test_skips_without_unprocessed_docs(self, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        from pipeline.stages.e2_llm import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "No unprocessed documents" in result["reason"]

    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.service.LLMService.call")
    @patch("pipeline.llm.service.LLMService._ensure_client")
    def test_runs_successfully_with_mock(self, mock_ensure, mock_call, mock_extract, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        stmts_dir = tmp_path / "data" / "financial_statements"
        stmts_dir.mkdir(parents=True)
        (stmts_dir / "btg_informe_2024.pdf").write_text("fake content")

        mock_extract.return_value = "Investment report content"
        mock_call.return_value = make_llm_call_result(make_e2_llm_output())

        from pipeline.stages.e2_llm import run
        result = run(ctx)

        assert result["success"] is True
        assert result["total_processed"] == 1
        assert result["total_errors"] == 0
        assert result["processed"][0]["transactions"] == 1
        assert result["processed"][0]["investments"] == 1
        assert result["queued"]["total"] == 1
        assert result["queued"]["by_data_subdir"].get("financial_statements") == 1
        assert result["e2_llm_settings"]["workers"] == 1

    def test_e2_llm_perf_settings_defaults(self, tmp_path):
        from pipeline.stages.e2_llm import _e2_llm_perf_settings

        ctx = make_llm_ctx(tmp_path)
        perf = _e2_llm_perf_settings(ctx)
        assert perf["concurrency"] == 4
        assert perf["max_input_chars"] == 40_000
        assert perf["max_pdf_pages"] == 35

    def test_e2_llm_queue_stats_groups_by_data_subdir(self, tmp_path):
        from pipeline.stages.e2_llm import _e2_llm_queue_stats

        data_dir = tmp_path / "data"
        fs = data_dir / "financial_statements"
        ir = data_dir / "income_tax_br"
        fs.mkdir(parents=True)
        ir.mkdir(parents=True)
        a = fs / "a.pdf"
        b = fs / "sub" / "b.pdf"
        c = ir / "c.pdf"
        for p in (a, b, c):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x")

        stats = _e2_llm_queue_stats(data_dir, [a, b, c])
        assert stats == {"financial_statements": 2, "income_tax_br": 1}

    def test_find_unprocessed_docs_skips_already_extracted(self, tmp_path):
        ctx = make_llm_ctx(tmp_path)
        stmts_dir = tmp_path / "data" / "financial_statements"
        stmts_dir.mkdir(parents=True)
        (stmts_dir / "itau_extrato-0_original.csv").write_text("x")
        (stmts_dir / "btg_informe.pdf").write_text("x")

        # A6a: usa store.write para criar o artefato existente.
        store = ctx.get_artifact_store()
        store.write("E2", "itau_extrato", {"dummy": True})

        from pipeline.stages.e2_llm import _find_unprocessed_docs
        docs = _find_unprocessed_docs(ctx, store)
        names = [d.name for d in docs]
        assert "btg_informe.pdf" in names
        assert "itau_extrato-0_original.csv" not in names

    def test_find_unprocessed_docs_skips_income_tax_br_when_extract_exists(self, tmp_path):
        """Regression: IRPF/informes must not be re-queued every run once E2 JSON exists."""
        ctx = make_llm_ctx(tmp_path)
        irpf_dir = tmp_path / "data" / "income_tax_br"
        irpf_dir.mkdir(parents=True)
        (irpf_dir / "irpf_2024.pdf").write_text("x")

        # A6a: usa store.write para criar o artefato existente.
        store = ctx.get_artifact_store()
        store.write("E2-llm", "irpf_2024", {"dummy": True})

        from pipeline.stages.e2_llm import _find_unprocessed_docs

        docs = _find_unprocessed_docs(ctx, store)
        assert docs == []


# ══════════════════════════════════════════════════════════════════════════
# A6a — CRITÉRIOS ESTRUTURAIS (ADR-105)
# ══════════════════════════════════════════════════════════════════════════

_REPO = Path(__file__).resolve().parents[1]


class TestA6aStructural:
    """Verifica que E1.5 e E2-llm escrevem via ArtifactStore (não disco direto)."""

    def test_e15_does_not_write_text_directly(self):
        src = (_REPO / "pipeline" / "stages" / "e15.py").read_text(encoding="utf-8")
        assert "write_text" not in src, (
            "pipeline/stages/e15.py não deve escrever direto em disco — "
            "A6a migrou para store.write('E1.5', ...)."
        )
        assert "store.write" in src, (
            "pipeline/stages/e15.py deve chamar store.write após A6a."
        )

    def test_e2_llm_does_not_write_text_directly_in_process_one(self):
        src = (_REPO / "pipeline" / "stages" / "e2_llm.py").read_text(encoding="utf-8")
        # O bloco de write dentro de _process_one_e2_llm_document não deve ter write_text
        assert "out_path.write_text" not in src, (
            "pipeline/stages/e2_llm.py não deve usar out_path.write_text — "
            "A6a migrou para store.write('E2-llm', ...)."
        )
        assert "store.write" in src, (
            "pipeline/stages/e2_llm.py deve chamar store.write após A6a."
        )

    def test_e15_writes_to_e15_stage_key(self, tmp_path):
        """Com DiskArtifactStore, E1.5 deve produzir baseline_patrimonial-1.5_baseline.json."""
        import json
        from unittest.mock import patch

        ctx = make_llm_ctx(tmp_path)
        (tmp_path / "data" / "income_tax_br").mkdir(parents=True)
        (tmp_path / "data" / "income_tax_br" / "irpf.pdf").write_text("x")

        with (
            patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract", return_value="x"),
            patch("pipeline.llm.service.LLMService._ensure_client"),
            patch("pipeline.llm.service.LLMService.call",
                  return_value=make_llm_call_result(make_e15_output())),
        ):
            from pipeline.stages.e15 import run
            result = run(ctx)

        assert result["success"] is True
        # A6a: arquivo correto via store
        baseline_path = ctx.e2_dir / "baseline_patrimonial-1.5_baseline.json"
        assert baseline_path.exists(), "E1.5 deve escrever baseline_patrimonial-1.5_baseline.json"
        # Arquivo E1.5c NÃO deve existir ainda (E1.5c ainda não rodou)
        consolidated = ctx.e2_dir / "baseline_patrimonial-1.5_consolidated.json"
        assert not consolidated.exists(), (
            "E1.5 não deve mais escrever _consolidated.json — isso é responsabilidade do E1.5c."
        )
        data = json.loads(baseline_path.read_text())
        assert data["resumo"]["patrimonio_liquido"] == 550000.00

    def test_e2_llm_writes_via_store(self, tmp_path):
        """Com DiskArtifactStore, E2-llm deve produzir {stem}-2_extract.json no path correto."""
        import json
        from unittest.mock import patch

        ctx = make_llm_ctx(tmp_path)
        stmts_dir = tmp_path / "data" / "financial_statements"
        stmts_dir.mkdir(parents=True)
        (stmts_dir / "btg_informe_2024.pdf").write_text("x")

        with (
            patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract",
                  return_value="Investment content"),
            patch("pipeline.llm.service.LLMService._ensure_client"),
            patch("pipeline.llm.service.LLMService.call",
                  return_value=make_llm_call_result(make_e2_llm_output())),
        ):
            from pipeline.stages.e2_llm import run
            result = run(ctx)

        assert result["success"] is True
        assert result["total_processed"] == 1
        # A6a: arquivo deve existir no path esperado do store
        out_file = ctx.e2_dir / "btg_informe_2024-2_extract.json"
        assert out_file.exists(), f"E2-llm deve escrever {out_file.name} via store"
        data = json.loads(out_file.read_text())
        assert data["extraido_por"] == "llm"
