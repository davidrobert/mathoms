#!/usr/bin/env python3
"""Tests for LLM stage wrappers (E1, E1.5, E2-llm) and validators.

All tests mock LLM calls — no real API keys needed.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.context import WorkspaceContext
from pipeline.llm.schemas.e1_members import (
    ExtractedAccount,
    ExtractedMember,
    MembersExtractOutput,
)
from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput, PatrimonialItem
from pipeline.llm.schemas.e2_llm_extract import (
    ExtractedInvestment,
    ExtractedTransaction,
    LLMExtractOutput,
)
from pipeline.llm.schemas.e7_review import (
    E7ReviewOutput,
    NarrativeSection,
    ReviewInsight,
    ScoreAdjustment,
)
from pipeline.llm.service import LLMCallResult
from pipeline.llm.validators import (
    ValidationResult,
    validate_e1_output,
    validate_e15_output,
    validate_e2_llm_output,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


def _make_ctx(tmp_path: Path) -> WorkspaceContext:
    """Create a WorkspaceContext with llm_config.json in config/."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    llm_config = {
        "provider": "anthropic",
        "api_key": "sk-test-fake",
        "model_name": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "temperature": 0.1,
    }
    (config_dir / "llm_config.json").write_text(json.dumps(llm_config))
    return WorkspaceContext(root=tmp_path)


def _make_ctx_no_llm(tmp_path: Path) -> WorkspaceContext:
    """Create a WorkspaceContext without llm_config.json."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    return WorkspaceContext(root=tmp_path)


def _mock_e1_output() -> MembersExtractOutput:
    return MembersExtractOutput(
        members=[
            ExtractedMember(
                key="david",
                full_name="David Ferreira Campos",
                short_name="David",
                cpf="12345678901",
                birth_date="1985-03-15",
                role="titular",
                accounts=[
                    ExtractedAccount(
                        institution_code="itau",
                        account_type="extratoconta",
                        agency="1234",
                        account_number="56789",
                    ),
                ],
            ),
            ExtractedMember(
                key="mariana",
                full_name="Mariana Ferreira Campos",
                short_name="Mariana",
                role="conjuge",
                accounts=[],
            ),
        ],
        titular_key="david",
        confidence=0.95,
        notes="Clear extraction from IRPF declaration",
    )


def _mock_e15_output() -> BaselinePatrimonialOutput:
    return BaselinePatrimonialOutput(
        items=[
            PatrimonialItem(
                code="01",
                description="Apartamento São Paulo",
                category="imovel",
                institution=None,
                value_brl=500000.00,
                member_key="david",
                year=2024,
            ),
            PatrimonialItem(
                code="41",
                description="Poupança Itaú",
                category="poupanca",
                institution="itau",
                value_brl=50000.00,
                member_key="david",
                year=2024,
            ),
        ],
        total_assets_brl=550000.00,
        total_liabilities_brl=0.0,
        net_worth_brl=550000.00,
        reference_year=2024,
        members_found=["david"],
        confidence=0.90,
        notes=None,
    )


def _mock_e2_llm_output() -> LLMExtractOutput:
    return LLMExtractOutput(
        source_file="btg_informe_2024.pdf",
        institution="btgpactual",
        document_type="investment_report",
        period="202412",
        member_key="david",
        currency="BRL",
        transactions=[
            ExtractedTransaction(
                date="2024-12-01",
                description="Resgate CDB",
                amount=10000.00,
            ),
        ],
        investments=[
            ExtractedInvestment(
                type="cdb",
                institution="btgpactual",
                description="CDB DI 100% CDI",
                value_brl=25000.00,
                applied_date="2024-06-15",
                maturity_date="2025-06-15",
                rate="100% CDI",
                member_key="david",
            ),
        ],
        confidence=0.88,
        notes="Investment report PDF",
    )


def _mock_call_result(output) -> LLMCallResult:
    return LLMCallResult(
        output=output,
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        tokens_in=1500,
        tokens_out=800,
        total_tokens=2300,
        cost_estimate_usd=0.0165,
        duration_ms=2500,
        retries_used=0,
    )


# ══════════════════════════════════════════════════════════════════════════
# VALIDATORS
# ══════════════════════════════════════════════════════════════════════════


class TestValidateE1Output:
    def test_valid_output(self):
        output = _mock_e1_output()
        result = validate_e1_output(output)
        assert result.valid
        assert len(result.errors) == 0

    def test_empty_members(self):
        """Schema has min_length=1 so empty list raises ValidationError.
        Validator should still handle if somehow bypassed."""
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            MembersExtractOutput(members=[], confidence=0.5)

    def test_duplicate_keys(self):
        output = MembersExtractOutput(
            members=[
                ExtractedMember(key="david", full_name="David A", short_name="David", role="titular"),
                ExtractedMember(key="david", full_name="David B", short_name="David2", role="titular"),
            ],
            confidence=0.8,
        )
        result = validate_e1_output(output)
        assert not result.valid
        assert any("duplicate" in e for e in result.errors)

    def test_uppercase_key_rejected(self):
        output = MembersExtractOutput(
            members=[
                ExtractedMember(key="David", full_name="David FC", short_name="David", role="titular"),
            ],
            confidence=0.8,
        )
        result = validate_e1_output(output)
        assert not result.valid
        assert any("lowercase" in e for e in result.errors)

    def test_key_with_spaces_rejected(self):
        output = MembersExtractOutput(
            members=[
                ExtractedMember(key="david fc", full_name="David FC", short_name="David", role="titular"),
            ],
            confidence=0.8,
        )
        result = validate_e1_output(output)
        assert not result.valid

    def test_titular_key_not_in_members(self):
        output = MembersExtractOutput(
            members=[
                ExtractedMember(key="david", full_name="David", short_name="David", role="titular"),
            ],
            titular_key="unknown",
            confidence=0.8,
        )
        result = validate_e1_output(output)
        assert not result.valid
        assert any("titular_key" in e for e in result.errors)

    def test_invalid_cpf_warns(self):
        output = MembersExtractOutput(
            members=[
                ExtractedMember(key="david", full_name="David", short_name="David", role="titular", cpf="123"),
            ],
            confidence=0.8,
        )
        result = validate_e1_output(output)
        assert result.valid
        assert any("CPF" in w for w in result.warnings)

    def test_no_titular_role_warns(self):
        output = MembersExtractOutput(
            members=[
                ExtractedMember(key="david", full_name="David", short_name="David", role="dependente"),
            ],
            confidence=0.8,
        )
        result = validate_e1_output(output)
        assert result.valid
        assert any("titular" in w for w in result.warnings)

    def test_empty_full_name(self):
        output = MembersExtractOutput(
            members=[
                ExtractedMember(key="david", full_name="", short_name="David", role="titular"),
            ],
            confidence=0.8,
        )
        result = validate_e1_output(output)
        assert not result.valid
        assert any("empty full_name" in e for e in result.errors)


class TestValidateE15Output:
    def test_valid_output(self):
        output = _mock_e15_output()
        result = validate_e15_output(output)
        assert result.valid

    def test_missing_member_key(self):
        output = BaselinePatrimonialOutput(
            items=[
                PatrimonialItem(
                    code="01", description="Apt", category="imovel",
                    value_brl=100000, member_key="", year=2024,
                ),
            ],
            reference_year=2024, confidence=0.8,
        )
        result = validate_e15_output(output)
        assert not result.valid
        assert any("member_key" in e for e in result.errors)

    def test_invalid_reference_year(self):
        output = BaselinePatrimonialOutput(
            items=[], reference_year=1999, confidence=0.8,
        )
        result = validate_e15_output(output)
        assert not result.valid
        assert any("reference_year" in e for e in result.errors)

    def test_non_standard_category_warns(self):
        output = BaselinePatrimonialOutput(
            items=[
                PatrimonialItem(
                    code="99", description="Crypto", category="criptomoeda",
                    value_brl=5000, member_key="david", year=2024,
                ),
            ],
            reference_year=2024, confidence=0.8,
        )
        result = validate_e15_output(output)
        assert result.valid
        assert any("non-standard" in w for w in result.warnings)

    def test_totals_mismatch_warns(self):
        output = BaselinePatrimonialOutput(
            items=[
                PatrimonialItem(
                    code="41", description="Poup", category="poupanca",
                    value_brl=10000, member_key="david", year=2024,
                ),
            ],
            total_assets_brl=99999,
            reference_year=2024, confidence=0.8,
        )
        result = validate_e15_output(output)
        assert result.valid
        assert any("total_assets_brl" in w for w in result.warnings)


class TestValidateE2LLMOutput:
    def test_valid_output(self):
        output = _mock_e2_llm_output()
        result = validate_e2_llm_output(output)
        assert result.valid

    def test_missing_source_file(self):
        output = LLMExtractOutput(
            source_file="",
            institution="itau",
            document_type="extrato",
            confidence=0.8,
        )
        result = validate_e2_llm_output(output)
        assert not result.valid
        assert any("source_file" in e for e in result.errors)

    def test_missing_institution(self):
        output = LLMExtractOutput(
            source_file="test.pdf",
            institution="",
            document_type="extrato",
            confidence=0.8,
        )
        result = validate_e2_llm_output(output)
        assert not result.valid
        assert any("institution" in e for e in result.errors)

    def test_invalid_transaction_date(self):
        output = LLMExtractOutput(
            source_file="test.pdf",
            institution="itau",
            document_type="extrato",
            transactions=[
                ExtractedTransaction(
                    date="01/12/2024",
                    description="Compra",
                    amount=-100,
                ),
            ],
            confidence=0.8,
        )
        result = validate_e2_llm_output(output)
        assert not result.valid
        assert any("YYYY-MM-DD" in e for e in result.errors)

    def test_non_standard_investment_type_warns(self):
        output = LLMExtractOutput(
            source_file="test.pdf",
            institution="btg",
            document_type="investment_report",
            investments=[
                ExtractedInvestment(
                    type="debenture",
                    institution="btg",
                    description="Debenture XYZ",
                    value_brl=10000,
                ),
            ],
            confidence=0.8,
        )
        result = validate_e2_llm_output(output)
        assert result.valid
        assert any("non-standard" in w for w in result.warnings)

    def test_invalid_period_warns(self):
        output = LLMExtractOutput(
            source_file="test.pdf",
            institution="itau",
            document_type="extrato",
            period="2024-12",
            confidence=0.8,
        )
        result = validate_e2_llm_output(output)
        assert result.valid
        assert any("YYYYMM" in w for w in result.warnings)

    def test_no_transactions_no_investments_warns(self):
        output = LLMExtractOutput(
            source_file="test.pdf",
            institution="itau",
            document_type="extrato",
            confidence=0.8,
        )
        result = validate_e2_llm_output(output)
        assert result.valid
        assert any("no transactions" in w for w in result.warnings)


class TestValidationResult:
    def test_empty_is_valid(self):
        r = ValidationResult()
        assert r.valid
        assert r.to_dict()["valid"] is True

    def test_with_error_is_invalid(self):
        r = ValidationResult()
        r.error("something wrong")
        assert not r.valid
        assert r.to_dict()["errors"] == ["something wrong"]

    def test_with_warning_still_valid(self):
        r = ValidationResult()
        r.warn("heads up")
        assert r.valid
        assert r.to_dict()["warnings"] == ["heads up"]


# ══════════════════════════════════════════════════════════════════════════
# E1 STAGE RUNNER
# ══════════════════════════════════════════════════════════════════════════


class TestE1Stage:
    def test_skips_without_llm_config(self, tmp_path):
        ctx = _make_ctx_no_llm(tmp_path)
        from pipeline.stages.e1 import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "free tier" in result["reason"]

    def test_skips_without_documents(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        from pipeline.stages.e1 import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "No personal documents" in result["reason"]

    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.service.LLMService.call")
    @patch("pipeline.llm.service.LLMService._ensure_client")
    def test_runs_successfully_with_mock(self, mock_ensure, mock_call, mock_extract, tmp_path):
        ctx = _make_ctx(tmp_path)
        (tmp_path / "data" / "income_tax_br").mkdir(parents=True)
        (tmp_path / "data" / "income_tax_br" / "irpf_2024.pdf").write_text("fake pdf content")

        mock_extract.return_value = "IRPF 2024 content here"
        mock_call.return_value = _mock_call_result(_mock_e1_output())

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
        ctx = _make_ctx(tmp_path)
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
        ctx = _make_ctx_no_llm(tmp_path)
        from pipeline.stages.e15 import run
        result = run(ctx)
        assert result["skipped"] is True

    def test_skips_without_documents(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        from pipeline.stages.e15 import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "No IRPF" in result["reason"]

    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.service.LLMService.call")
    @patch("pipeline.llm.service.LLMService._ensure_client")
    def test_runs_successfully_with_mock(self, mock_ensure, mock_call, mock_extract, tmp_path):
        ctx = _make_ctx(tmp_path)
        (tmp_path / "data" / "income_tax_br").mkdir(parents=True)
        (tmp_path / "data" / "income_tax_br" / "irpf_2024.pdf").write_text("fake content")

        mock_extract.return_value = "IRPF data here"
        mock_call.return_value = _mock_call_result(_mock_e15_output())

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
        ctx = _make_ctx_no_llm(tmp_path)
        from pipeline.stages.e2_llm import run
        result = run(ctx)
        assert result["skipped"] is True

    def test_skips_without_unprocessed_docs(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        from pipeline.stages.e2_llm import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "No unprocessed documents" in result["reason"]

    @patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract")
    @patch("pipeline.llm.service.LLMService.call")
    @patch("pipeline.llm.service.LLMService._ensure_client")
    def test_runs_successfully_with_mock(self, mock_ensure, mock_call, mock_extract, tmp_path):
        ctx = _make_ctx(tmp_path)
        stmts_dir = tmp_path / "data" / "financial_statements"
        stmts_dir.mkdir(parents=True)
        (stmts_dir / "btg_informe_2024.pdf").write_text("fake content")

        mock_extract.return_value = "Investment report content"
        mock_call.return_value = _mock_call_result(_mock_e2_llm_output())

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

        ctx = _make_ctx(tmp_path)
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
        ctx = _make_ctx(tmp_path)
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
        ctx = _make_ctx(tmp_path)
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

        ctx = _make_ctx(tmp_path)
        (tmp_path / "data" / "income_tax_br").mkdir(parents=True)
        (tmp_path / "data" / "income_tax_br" / "irpf.pdf").write_text("x")

        with (
            patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract", return_value="x"),
            patch("pipeline.llm.service.LLMService._ensure_client"),
            patch("pipeline.llm.service.LLMService.call",
                  return_value=_mock_call_result(_mock_e15_output())),
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

        ctx = _make_ctx(tmp_path)
        stmts_dir = tmp_path / "data" / "financial_statements"
        stmts_dir.mkdir(parents=True)
        (stmts_dir / "btg_informe_2024.pdf").write_text("x")

        with (
            patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract",
                  return_value="Investment content"),
            patch("pipeline.llm.service.LLMService._ensure_client"),
            patch("pipeline.llm.service.LLMService.call",
                  return_value=_mock_call_result(_mock_e2_llm_output())),
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


# ══════════════════════════════════════════════════════════════════════════
# OUTPUT CONVERTERS
# ══════════════════════════════════════════════════════════════════════════


class TestOutputConverters:
    def test_e1_output_to_family_members_json(self):
        from pipeline.stages.e1 import _output_to_family_members_json
        output = _mock_e1_output()
        result = _output_to_family_members_json(output)

        assert "david" in result["membros"]
        assert result["membros"]["david"]["nome_completo"] == "David Ferreira Campos"
        assert result["membros"]["david"]["cpf"] == "12345678901"
        assert result["banco_membro"]["itau"] == "david"
        assert result["titular"] == "david"

    def test_e15_output_to_baseline_json(self):
        from pipeline.stages.e15 import _output_to_baseline_json
        output = _mock_e15_output()
        result = _output_to_baseline_json(output)

        assert len(result["itens"]) == 2
        assert result["resumo"]["patrimonio_liquido"] == 550000.00
        assert result["_meta"]["source"] == "E1.5-llm"
        assert result["_meta"]["confidence"] == 0.90

    def test_e2_llm_output_to_e2_json(self):
        from pipeline.stages.e2_llm import _output_to_e2_json
        output = _mock_e2_llm_output()
        result = _output_to_e2_json(output)

        assert result["instituicao"] == "btgpactual"
        assert result["extraido_por"] == "llm"
        assert len(result["transacoes"]) == 1
        assert len(result["investimentos"]) == 1
        assert result["investimentos"][0]["taxa"] == "100% CDI"
        assert result["periodo"]["inicio"] == "2024-12-01"
        assert result["periodo"]["fim"] == "2024-12-31"


# ══════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR INTEGRATION
# ══════════════════════════════════════════════════════════════════════════


def _mock_e7_review_output() -> E7ReviewOutput:
    return E7ReviewOutput(
        insights=[
            ReviewInsight(
                category="patrimonio",
                severity="info",
                title="Patrimônio concentrado",
                description="72% em imóvel.",
                recommendation="Diversificar.",
            ),
        ],
        recommendations=["Diversificar investimentos"],
        score_adjustments=[
            ScoreAdjustment(
                factor="diversificacao",
                original_value=70.0,
                adjustment=-10.0,
                reason="100% renda fixa",
            ),
        ],
        narrative_sections=[
            NarrativeSection(
                section_key="resumo_executivo",
                title="Resumo Executivo",
                content="Situação financeira estável.",
            ),
        ],
        overall_assessment="Saúde financeira moderada.",
        risk_level="moderate",
        confidence=0.85,
    )


# ══════════════════════════════════════════════════════════════════════════
# E7-REVIEW STAGE RUNNER
# ══════════════════════════════════════════════════════════════════════════


class TestE7ReviewStage:
    def test_skips_without_llm_config(self, tmp_path):
        ctx = _make_ctx_no_llm(tmp_path)
        from pipeline.stages.e7_review_llm import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "free tier" in result["reason"]

    def test_skips_without_e5_analysis(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        from pipeline.stages.e7_review_llm import run
        result = run(ctx)
        assert result["skipped"] is True
        assert "E5" in result["reason"]

    @patch("pipeline.llm.service.LLMService.call")
    @patch("pipeline.llm.service.LLMService._ensure_client")
    def test_runs_successfully_with_mock(self, mock_ensure, mock_call, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.e5_dir.mkdir(parents=True)
        (ctx.e5_dir / "analise_financeira-5_analysis.json").write_text(
            json.dumps({"score": 70, "patrimonio_liquido": 897000})
        )

        mock_call.return_value = _mock_call_result(_mock_e7_review_output())

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
        output = _mock_e7_review_output()
        result = _output_to_review_json(output)

        assert result["nivel_risco"] == "moderate"
        assert result["avaliacao_geral"] == "Saúde financeira moderada."
        assert len(result["insights"]) == 1
        assert result["insights"][0]["categoria"] == "patrimonio"
        assert len(result["ajustes_score"]) == 1
        assert result["ajustes_score"][0]["ajuste"] == -10.0
        assert "resumo_executivo" in result["narrativas"]
        assert result["_meta"]["source"] == "E7-review-llm"


class TestOrchestratorLLMStages:
    def test_get_stage_runner_returns_callable_for_llm_stages(self):
        from pipeline.orchestrator import _get_stage_runner
        for stage in ["E1", "E1.5", "E2-llm", "E7-review"]:
            runner = _get_stage_runner(stage)
            assert runner is not None, f"No runner for {stage}"
            assert callable(runner)

    def test_llm_stages_skipped_when_skip_llm_true(self):
        from pipeline.orchestrator import run_stages, LLM_STAGES
        ctx = WorkspaceContext.default()
        result = run_stages(ctx, ["E1", "E1.5"], skip_llm=True)
        for sr in result.stages:
            assert sr.success
            assert sr.detail.get("skipped") is True

    def test_full_order_has_correct_sequence(self):
        from pipeline.orchestrator import FULL_ORDER
        e1_idx = FULL_ORDER.index("E1")
        e15_idx = FULL_ORDER.index("E1.5")
        e15c_idx = FULL_ORDER.index("E1.5c")
        e2_llm_idx = FULL_ORDER.index("E2-llm")
        e2_fat_idx = FULL_ORDER.index("E2-faturas")

        e2_ext_idx = FULL_ORDER.index("E2-extratos")
        # E2 determinístico antes do E2-llm — só o que falhar no parser vai à IA.
        assert e1_idx < e15_idx < e15c_idx < e2_fat_idx < e2_ext_idx < e2_llm_idx
