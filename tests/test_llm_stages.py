#!/usr/bin/env python3
"""Tests for LLM stage validators, output converters, and orchestrator
integration (E1, E1.5, E2-llm).

Stage-runner tests live in `tests/test_llm_stages_per_stage.py`.
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
from pipeline.llm.schemas.e2_llm_extract import (
    ExtractedInvestment,
    ExtractedTransaction,
    LLMExtractOutput,
)
from pipeline.llm.schemas.e15_baseline import (
    BaselinePatrimonialOutput,
    PatrimonialItem,
)
from pipeline.llm.validators import (
    ValidationResult,
    validate_e1_output,
    validate_e2_llm_output,
    validate_e15_output,
)
from tests._llm_stage_fixtures import (
    make_e1_output,
    make_e2_llm_output,
    make_e15_output,
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
                ExtractedMember(
                    key="david", full_name="David A", short_name="David", role="titular"
                ),
                ExtractedMember(
                    key="david", full_name="David B", short_name="David2", role="titular"
                ),
            ],
            confidence=0.8,
        )
        result = validate_e1_output(output)
        assert not result.valid
        assert any("duplicate" in e for e in result.errors)

    def test_uppercase_key_rejected(self):
        output = MembersExtractOutput(
            members=[
                ExtractedMember(
                    key="David", full_name="David FC", short_name="David", role="titular"
                ),
            ],
            confidence=0.8,
        )
        result = validate_e1_output(output)
        assert not result.valid
        assert any("lowercase" in e for e in result.errors)

    def test_key_with_spaces_rejected(self):
        output = MembersExtractOutput(
            members=[
                ExtractedMember(
                    key="david fc", full_name="David FC", short_name="David", role="titular"
                ),
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

    def test_cpf_present_flag_does_not_warn(self):
        """ADR-259 §2 (A20.l15): schema só carrega o flag — nada de validação de formato."""
        output = MembersExtractOutput(
            members=[
                ExtractedMember(
                    key="david",
                    full_name="David",
                    short_name="David",
                    role="titular",
                    cpf_present=True,
                ),
            ],
            confidence=0.8,
        )
        result = validate_e1_output(output)
        assert result.valid
        assert not any("CPF" in w for w in result.warnings)

    def test_no_titular_role_warns(self):
        output = MembersExtractOutput(
            members=[
                ExtractedMember(
                    key="david", full_name="David", short_name="David", role="dependente"
                ),
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
                    code="01",
                    description="Apt",
                    category="imovel",
                    value_brl=100000,
                    member_key="",
                    year=2024,
                ),
            ],
            reference_year=2024,
            confidence=0.8,
        )
        result = validate_e15_output(output)
        assert not result.valid
        assert any("member_key" in e for e in result.errors)

    def test_invalid_reference_year(self):
        output = BaselinePatrimonialOutput(
            items=[],
            reference_year=1999,
            confidence=0.8,
        )
        result = validate_e15_output(output)
        assert not result.valid
        assert any("reference_year" in e for e in result.errors)

    def test_non_standard_category_warns(self):
        output = BaselinePatrimonialOutput(
            items=[
                PatrimonialItem(
                    code="99",
                    description="Crypto",
                    category="criptomoeda",
                    value_brl=5000,
                    member_key="david",
                    year=2024,
                ),
            ],
            reference_year=2024,
            confidence=0.8,
        )
        result = validate_e15_output(output)
        assert result.valid
        assert any("non-standard" in w for w in result.warnings)

    def test_totals_mismatch_warns(self):
        output = BaselinePatrimonialOutput(
            items=[
                PatrimonialItem(
                    code="41",
                    description="Poup",
                    category="poupanca",
                    value_brl=10000,
                    member_key="david",
                    year=2024,
                ),
            ],
            total_assets_brl=99999,
            reference_year=2024,
            confidence=0.8,
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
        from pipeline.stages.extract_members import _output_to_family_members_json

        output = make_e1_output()
        result = _output_to_family_members_json(output)

        assert "david" in result["membros"]
        assert result["membros"]["david"]["nome_completo"] == "David Ferreira Campos"
        # ADR-259 §2 (A20.l15): artifact carrega só o flag — nunca o CPF cru.
        assert result["membros"]["david"]["cpf_present"] is True
        assert "cpf" not in result["membros"]["david"]
        assert result["banco_membro"]["itau"] == "david"
        assert result["titular"] == "david"

    def test_e15_output_to_baseline_json(self):
        from pipeline.stages.extract_baseline import _output_to_baseline_json

        output = make_e15_output()
        result = _output_to_baseline_json(output)

        assert len(result["itens"]) == 2
        # String decimal no artifact (A20.l11 / ADR-090).
        assert result["resumo"]["patrimonio_liquido"] == "550000.00"
        assert result["_meta"]["source"] == "E1.5-llm"
        assert result["_meta"]["confidence"] == 0.90

    def test_e2_llm_output_to_e2_json(self):
        from pipeline.stages.extract_with_llm import _output_to_e2_json

        output = make_e2_llm_output()
        result = _output_to_e2_json(output)

        assert result["banco"] == "btgpactual"
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

        for stage in ["E1", "E1.5", "extract_with_llm"]:
            runner = _get_stage_runner(stage)
            assert runner is not None, f"No runner for {stage}"
            assert callable(runner)

    def test_llm_stages_skipped_when_skip_llm_true(self):
        from pipeline.orchestrator import LLM_STAGES, run_stages

        ctx = WorkspaceContext.default()
        result = run_stages(ctx, ["E1", "E1.5"], skip_llm=True)
        for sr in result.stages:
            assert sr.success
            assert sr.detail.get("skipped") is True

    def test_full_order_has_correct_sequence(self):
        from pipeline.orchestrator import FULL_ORDER

        e1_idx = FULL_ORDER.index("extract_members")
        e15_idx = FULL_ORDER.index("extract_baseline")
        e15c_idx = FULL_ORDER.index("consolidate_baseline")
        e2_llm_idx = FULL_ORDER.index("extract_with_llm")
        e2_fat_idx = FULL_ORDER.index("extract_invoices")

        e2_ext_idx = FULL_ORDER.index("extract_statements")
        # E2 determinístico antes do extract_with_llm — só o que falhar no parser vai à IA.
        assert e1_idx < e15_idx < e15c_idx < e2_fat_idx < e2_ext_idx < e2_llm_idx


# ══════════════════════════════════════════════════════════════════════════
# A28.l8 — HIGIENE DE INGESTÃO E2-llm (banco vazio → needs_review)
# ══════════════════════════════════════════════════════════════════════════


class TestE2LLMIngestHygiene:
    def test_output_to_e2_json_emits_banco(self):
        # from_e2_dict lê `banco` (não `instituicao`); sem ele a key E3
        # degradava para "_extrato_..." (dogfood 72883bde). Pós-ADR-312 o
        # writer é canonical-only — `instituicao` não é mais emitido.
        from pipeline.stages.extract_with_llm import _output_to_e2_json

        e2 = _output_to_e2_json(make_e2_llm_output())

        assert e2["banco"] == "btgpactual"

    def test_needs_review_entry_carries_review_reason(self):
        from pipeline.stages.extract_with_llm import _needs_review_entry

        output = make_e2_llm_output()
        entry = _needs_review_entry("doc_sem_banco.pdf", output)

        assert entry["needs_review"] is True
        assert entry["output"] is None
        assert entry["review_reason"]["code"] == "extract.missing_required_field"
        assert entry["review_reason"]["stage"] == "extract_with_llm"

    def test_validation_block_flags_only_needs_review_docs(self):
        from pipeline.stages.extract_with_llm import (
            _e2llm_validation_block,
            _needs_review_entry,
        )

        ok = {"file": "ok.pdf", "output": "ok-2_extract.json"}
        flagged = _needs_review_entry("sem_banco.pdf", make_e2_llm_output())

        block = _e2llm_validation_block([ok, flagged])

        assert block["valid"] is False
        assert len(block["review_reasons"]) == 1
        assert "sem_banco.pdf" in block["errors"][0]

    def test_validation_block_valid_when_all_ok(self):
        from pipeline.stages.extract_with_llm import _e2llm_validation_block

        block = _e2llm_validation_block([{"file": "ok.pdf", "output": "x"}])

        assert block == {"valid": True, "errors": [], "review_reasons": []}
