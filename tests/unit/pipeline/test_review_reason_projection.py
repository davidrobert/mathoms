"""Unit tests Fase 2 (ADR-272) — projeção producer→ReviewReason, map de vocabulário, drift e redação. CPFs vêm do gerador mod-11 (tests/utils/cpf), jamais CPF real (LGPD)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.domain.review_reason_projection import project_review_reasons
from pipeline.domain.services.debt_warnings import DebtVsIrpfDeclaracaoConflict
from pipeline.llm.validators import (
    _E15_RULES,
    _REVIEW_REASON_MAP,
    ValidationIssue,
)
from tests.utils.cpf import cpf_formatted

_KW = dict(
    stage="extract_baseline",
    artifact_key="irpfdeclaracao_2024",  # gitleaks:allow — artifact-key fixture, não secret
    document_id=None,
)


def _issue(code: str, **context) -> ValidationIssue:
    return ValidationIssue(code=code, severity="warning", context=dict(context))


class TestMapDrift:
    def test_every_e15_rule_code_is_mapped(self) -> None:
        # Drift guard: code emitido por _emit_e15 sem entrada no map vira ReviewReason
        # silenciosamente descartado. Falha aqui força adicionar a projeção.
        missing = set(_E15_RULES) - set(_REVIEW_REASON_MAP)
        assert not missing, f"e15.* sem mapeamento ReviewReason: {sorted(missing)}"

    def test_map_only_targets_existing_codes(self) -> None:
        for code, (rr_code, *_rest) in _REVIEW_REASON_MAP.items():
            assert isinstance(rr_code, ReviewReasonCode), code


class TestValidationIssueProjection:
    def test_unmapped_code_returns_none(self) -> None:
        assert _issue("legacy.unmigrated").to_review_reason(**_KW) is None

    def test_all_mapped_codes_project_to_declared_target(self) -> None:
        for code, (rr_code, message, expected, _keys) in _REVIEW_REASON_MAP.items():
            rr = _issue(
                code, index=0, category="x", year=1999, reference_year=1999
            ).to_review_reason(**_KW)
            assert rr is not None, code
            assert rr.code == rr_code
            assert rr.message == message
            assert rr.expected == expected
            assert rr.stage == "extract_baseline"
            assert rr.artifact_key == "irpfdeclaracao_2024"  # gitleaks:allow — fixture, não secret

    def test_non_monetary_offending_value_surfaces_context(self) -> None:
        rr = _issue("e15.item.invalid_year", index=2, year=1850).to_review_reason(**_KW)
        assert rr is not None
        assert "index=2" in rr.offending_value
        assert "year=1850" in rr.offending_value

    def test_monetary_offending_value_is_omitted(self) -> None:
        rr = _issue("e15.totals.assets_mismatch").to_review_reason(**_KW)
        assert rr is not None
        assert rr.offending_value == "(valores monetarios omitidos)"

    def test_offending_value_falls_back_when_keys_absent(self) -> None:
        rr = _issue("e15.item.empty_code").to_review_reason(**_KW)
        assert rr is not None
        assert rr.offending_value == "(sem detalhe)"


class TestRedactionDefenseInDepth:
    def test_cpf_leaking_into_context_is_masked_in_offending_value(self) -> None:
        # category não deveria carregar CPF, mas se vazar o __post_init__ mascara.
        cpf = cpf_formatted(seed=42)
        rr = _issue("e15.item.non_standard_category", index=1, category=cpf).to_review_reason(**_KW)
        assert rr is not None
        assert cpf not in rr.offending_value
        assert "***.***.***-**" in rr.offending_value


class TestProjectorAggregation:
    def test_groups_by_coarse_code_summing_occurrence_count(self) -> None:
        # 3 issues granulares → 1 ReviewReasonCode (extract_missing_required_field).
        issues = [
            _issue("e15.item.empty_code", index=0),
            _issue("e15.item.empty_description", index=1),
            _issue("e15.item.missing_member_key", index=2),
        ]
        reasons = project_review_reasons(issues, **_KW)
        assert len(reasons) == 1
        assert reasons[0].code == ReviewReasonCode.extract_missing_required_field
        assert reasons[0].occurrence_count == 3

    def test_distinct_codes_stay_separate(self) -> None:
        issues = [
            _issue("e15.item.empty_code", index=0),
            _issue("e15.item.invalid_year", index=1, year=1700),
        ]
        reasons = project_review_reasons(issues, **_KW)
        codes = {r.code for r in reasons}
        assert codes == {
            ReviewReasonCode.extract_missing_required_field,
            ReviewReasonCode.domain_validation_conflict,
        }

    def test_unmapped_producers_dropped_not_raised(self) -> None:
        issues = [_issue("legacy.unmigrated"), _issue("e15.items.empty")]
        reasons = project_review_reasons(issues, **_KW)
        assert len(reasons) == 1
        assert reasons[0].code == ReviewReasonCode.extract_missing_required_field

    def test_empty_producers_yield_empty(self) -> None:
        assert project_review_reasons([], **_KW) == []


class TestDomainWarningProjection:
    def test_debt_conflict_projects_without_monetary_leak(self) -> None:
        warning = DebtVsIrpfDeclaracaoConflict(
            member_key="casal",
            soma_debt_brl=Decimal("123456.78"),
            total_dividas_irpf_brl=Decimal("100000.00"),
            ratio=Decimal("1.23"),
        )
        rr = warning.to_review_reason(
            stage="reconcile_transactions", artifact_key="k", document_id=None
        )
        assert rr.code == ReviewReasonCode.domain_validation_conflict
        assert "123456.78" not in rr.offending_value
        assert "100000" not in rr.offending_value
        assert "ratio=1.23" in rr.offending_value


class TestParity:
    def test_review_reason_codes_subset_of_issue_codes(self) -> None:
        # review_reasons é projeção pobre de issues: todo code projetado tem origem
        # numa issue do mesmo pass; nunca há reason sem issue correspondente.
        issues = [
            _issue("e15.item.empty_code", index=0),
            _issue("e15.totals.assets_mismatch"),
            _issue("legacy.unmigrated"),
        ]
        reasons = project_review_reasons(issues, **_KW)
        assert {r.code for r in reasons} <= {
            ReviewReasonCode.extract_missing_required_field,
            ReviewReasonCode.domain_validation_conflict,
        }
        assert all(isinstance(r, ReviewReason) for r in reasons)
