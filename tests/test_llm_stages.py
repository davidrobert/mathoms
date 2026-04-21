#!/usr/bin/env python3
"""Tests for LLM stage validators, output converters, and orchestrator
integration (E1, E1.5, E2-llm, E7-review).

Stage-runner tests live in:
- `tests/test_llm_stages_per_stage.py` (E1, E1.5, E2-llm + A6a structural)
- `tests/test_llm_stages_e7.py` (E7-review)

Shared LLM output factories live in `tests/_llm_stage_fixtures.py`.

All tests mock LLM calls — no real API keys needed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.context import WorkspaceContext
from pipeline.llm.schemas.e1_members import (
    ExtractedMember,
    MembersExtractOutput,
)
from pipeline.llm.schemas.e15_baseline import (
    BaselinePatrimonialOutput,
    PatrimonialItem,
)
from pipeline.llm.schemas.e2_llm_extract import (
    ExtractedInvestment,
    ExtractedTransaction,
    LLMExtractOutput,
)
from pipeline.llm.validators import (
    ValidationResult,
    validate_e1_output,
    validate_e15_output,
    validate_e2_llm_output,
)
from tests._llm_stage_fixtures import (
    make_e1_output,
    make_e15_output,
    make_e2_llm_output,
)


# ══════════════════════════════════════════════════════════════════════════
# VALIDATORS
# ══════════════════════════════════════════════════════════════════════════


class TestValidateE1Output:
    def test_valid_output(self):
        output = make_e1_output()
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
        output = make_e15_output()
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
        output = make_e2_llm_output()
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
# OUTPUT CONVERTERS
# ══════════════════════════════════════════════════════════════════════════


class TestOutputConverters:
    def test_e1_output_to_family_members_json(self):
        from pipeline.stages.e1 import _output_to_family_members_json
        output = make_e1_output()
        result = _output_to_family_members_json(output)

        assert "david" in result["membros"]
        assert result["membros"]["david"]["nome_completo"] == "David Ferreira Campos"
        assert result["membros"]["david"]["cpf"] == "12345678901"
        assert result["banco_membro"]["itau"] == "david"
        assert result["titular"] == "david"

    def test_e15_output_to_baseline_json(self):
        from pipeline.stages.e15 import _output_to_baseline_json
        output = make_e15_output()
        result = _output_to_baseline_json(output)

        assert len(result["itens"]) == 2
        assert result["resumo"]["patrimonio_liquido"] == 550000.00
        assert result["_meta"]["source"] == "E1.5-llm"
        assert result["_meta"]["confidence"] == 0.90

    def test_e2_llm_output_to_e2_json(self):
        from pipeline.stages.e2_llm import _output_to_e2_json
        output = make_e2_llm_output()
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
