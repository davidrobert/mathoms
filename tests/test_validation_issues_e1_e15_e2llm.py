"""ValidationIssue em E1/E1.5/E2-llm (ADR-165 onda 4) — codes registrados, paridade legacy."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.schemas.e1_members import (
    ExtractedAccount,
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
    validate_e1_output,
    validate_e2_llm_output,
    validate_e15_output,
)

# ---------------------------------------------------------------------------
# Codes esperados pela onda 4 — gate: nenhum site cai em legacy.unmigrated.
# ---------------------------------------------------------------------------

E1_KNOWN_CODES: set[str] = {
    "e1.members.empty",
    "e1.member.invalid_key",
    "e1.member.duplicate_key",
    "e1.member.empty_full_name",
    "e1.member.empty_short_name",
    "e1.member.unexpected_role",
    "e1.member.invalid_birth_date",
    "e1.account.missing_institution",
    "e1.account.non_standard_type",
    "e1.titular.unknown_key",
    "e1.titular.missing",
    "e1.titular.multiple",
}

E15_KNOWN_CODES: set[str] = {
    "e15.items.empty",
    "e15.item.empty_code",
    "e15.item.empty_description",
    "e15.item.non_standard_category",
    "e15.item.missing_member_key",
    "e15.item.invalid_year",
    "e15.totals.assets_mismatch",
    "e15.totals.net_worth_mismatch",
    "e15.contribuinte.invalid_reference_year",
}

E2LLM_KNOWN_CODES: set[str] = {
    "e2llm.missing.source_file",
    "e2llm.missing.institution",
    "e2llm.empty.no_data",
    "e2llm.transaction.invalid_date",
    "e2llm.transaction.empty_description",
    "e2llm.transaction.zero_amount",
    "e2llm.investment.non_standard_type",
    "e2llm.investment.missing_institution",
    "e2llm.investment.non_positive_value",
    "e2llm.investment.invalid_applied_date",
    "e2llm.investment.invalid_maturity_date",
    "e2llm.invalid_period_format",
}


# ---------------------------------------------------------------------------
# E1 — fixtures e tests
# ---------------------------------------------------------------------------


def _e1_member(
    *,
    key: str = "david",
    full_name: str = "David",
    short_name: str = "David",
    role: str = "titular",
    cpf_present: bool = False,
    birth_date: str | None = None,
    accounts: list[ExtractedAccount] | None = None,
) -> ExtractedMember:
    return ExtractedMember(
        key=key,
        full_name=full_name,
        short_name=short_name,
        role=role,
        cpf_present=cpf_present,
        birth_date=birth_date,
        accounts=accounts or [],
    )


def _e1_output(
    *,
    members: list[ExtractedMember] | None = None,
    titular_key: str | None = "david",
) -> MembersExtractOutput:
    """Build via construct() para bypass Pydantic e permitir testar caminho `members empty`."""
    return MembersExtractOutput.model_construct(
        members=members or [],
        titular_key=titular_key,
        confidence=1.0,
        notes=None,
    )


class TestE1Codes:
    def test_empty_members(self):
        out = _e1_output(members=[], titular_key=None)
        r = validate_e1_output(out)
        assert any(i.code == "e1.members.empty" for i in r.issues)
        assert "E1: no members extracted" in r.errors

    def test_invalid_key(self):
        out = _e1_output(members=[_e1_member(key="Bad Key")], titular_key=None)
        r = validate_e1_output(out)
        assert any(i.code == "e1.member.invalid_key" for i in r.issues)

    def test_duplicate_key(self):
        out = _e1_output(
            members=[_e1_member(key="david"), _e1_member(key="david", short_name="d2")],
            titular_key=None,
        )
        r = validate_e1_output(out)
        assert any(i.code == "e1.member.duplicate_key" for i in r.issues)

    def test_titular_unknown(self):
        out = _e1_output(members=[_e1_member(key="david")], titular_key="unknown")
        r = validate_e1_output(out)
        assert any(i.code == "e1.titular.unknown_key" for i in r.issues)

    def test_no_titular_warns(self):
        out = _e1_output(members=[_e1_member(role="filho")], titular_key=None)
        r = validate_e1_output(out)
        assert any(i.code == "e1.titular.missing" for i in r.issues)

    def test_no_legacy_unmigrated_in_e1(self):
        out = _e1_output(
            members=[
                _e1_member(
                    key="Bad Key", full_name="", short_name="", role="ghost", cpf_present=True
                ),
                _e1_member(key="Bad Key"),
            ],
            titular_key="unknown",
        )
        r = validate_e1_output(out)
        for issue in r.issues:
            assert (
                issue.code != "legacy.unmigrated"
            ), f"Site não migrado em validate_e1: {issue.legacy_message!r}"
            assert issue.code in E1_KNOWN_CODES, f"Code novo não registrado: {issue.code}"


# ---------------------------------------------------------------------------
# E1.5 — fixtures e tests
# ---------------------------------------------------------------------------


def _e15_item(
    *,
    code: str = "01",
    description: str = "Apto",
    category: str = "imovel",
    member_key: str = "david",
    value_brl="500000.00",  # string decimal — Decimal no boundary (A20.l11 / ADR-090)
    year: int = 2024,
) -> PatrimonialItem:
    return PatrimonialItem(
        code=code,
        description=description,
        category=category,
        member_key=member_key,
        value_brl=value_brl,
        year=year,
    )


def _e15_minimal(items: list, **overrides) -> BaselinePatrimonialOutput:
    defaults: dict = {
        "items": items,
        "total_assets_brl": Decimal("0"),
        "total_liabilities_brl": Decimal("0"),
        "net_worth_brl": Decimal("0"),
        "reference_year": 2024,
        "members_found": [],
        "confidence": 1.0,
    }
    # model_construct bypassa validação — coerce manual mantém o invariante
    # Decimal do schema mesmo quando o teste passa float/str no override.
    defaults.update(overrides)
    for money_field in ("total_assets_brl", "total_liabilities_brl", "net_worth_brl"):
        defaults[money_field] = Decimal(str(defaults[money_field]))
    return BaselinePatrimonialOutput.model_construct(**defaults)


class TestE15Codes:
    def test_items_empty(self):
        out = _e15_minimal(items=[])
        r = validate_e15_output(out)
        assert any(i.code == "e15.items.empty" for i in r.issues)

    def test_item_missing_member_key(self):
        item = _e15_item(member_key="")
        out = _e15_minimal(items=[item], total_assets_brl=500000.0, net_worth_brl=500000.0)
        r = validate_e15_output(out)
        assert any(i.code == "e15.item.missing_member_key" for i in r.issues)

    def test_item_invalid_year(self):
        item = _e15_item(year=1800)
        out = _e15_minimal(items=[item], total_assets_brl=500000.0, net_worth_brl=500000.0)
        r = validate_e15_output(out)
        assert any(i.code == "e15.item.invalid_year" for i in r.issues)

    def test_invalid_reference_year(self):
        out = _e15_minimal(items=[], reference_year=1500)
        r = validate_e15_output(out)
        assert any(i.code == "e15.contribuinte.invalid_reference_year" for i in r.issues)

    def test_no_legacy_unmigrated_in_e15(self):
        item = _e15_item(code="", description="", category="exotic", member_key="", year=1500)
        out = _e15_minimal(
            items=[item],
            total_assets_brl=999.0,
            net_worth_brl=999.0,
            reference_year=1500,
        )
        r = validate_e15_output(out)
        for issue in r.issues:
            assert (
                issue.code != "legacy.unmigrated"
            ), f"Site não migrado em validate_e15: {issue.legacy_message!r}"
            assert issue.code in E15_KNOWN_CODES, f"Code novo não registrado: {issue.code}"


# ---------------------------------------------------------------------------
# E2-llm — fixtures e tests
# ---------------------------------------------------------------------------


def _build_e2llm_full_violation() -> LLMExtractOutput:
    tx = ExtractedTransaction(date="bad", description="", amount=0.0)
    inv = ExtractedInvestment(
        type="exotic",
        institution="",
        description="x",
        value_brl=-1.0,
        applied_date="bad",
        maturity_date="bad",
    )
    return _e2_minimal(
        source_file="", institution="", transactions=[tx], investments=[inv], period="bad"
    )


def _e2_minimal(
    *,
    source_file: str = "extrato.pdf",
    institution: str = "itau",
    transactions: list | None = None,
    investments: list | None = None,
    period: str | None = None,
) -> LLMExtractOutput:
    return LLMExtractOutput.model_construct(
        source_file=source_file,
        institution=institution,
        document_type="extrato",
        period=period,
        member_key=None,
        currency="BRL",
        transactions=transactions or [],
        investments=investments or [],
        confidence=1.0,
        notes=None,
    )


class TestE2llmCodes:
    def test_missing_source_file(self):
        out = _e2_minimal(source_file="")
        r = validate_e2_llm_output(out)
        assert any(i.code == "e2llm.missing.source_file" for i in r.issues)

    def test_empty_no_data(self):
        out = _e2_minimal()
        r = validate_e2_llm_output(out)
        assert any(i.code == "e2llm.empty.no_data" for i in r.issues)

    def test_invalid_period(self):
        out = _e2_minimal(period="2026/01")
        r = validate_e2_llm_output(out)
        assert any(i.code == "e2llm.invalid_period_format" for i in r.issues)

    def test_transaction_invalid_date(self):
        tx = ExtractedTransaction(date="2026/01/15", description="x", amount=100.0)
        out = _e2_minimal(transactions=[tx])
        r = validate_e2_llm_output(out)
        assert any(i.code == "e2llm.transaction.invalid_date" for i in r.issues)

    def test_no_legacy_unmigrated_in_e2llm(self):
        out = _build_e2llm_full_violation()
        r = validate_e2_llm_output(out)
        for issue in r.issues:
            assert (
                issue.code != "legacy.unmigrated"
            ), f"Site não migrado em validate_e2_llm: {issue.legacy_message!r}"
            assert issue.code in E2LLM_KNOWN_CODES, f"Code novo não registrado: {issue.code}"


# ---------------------------------------------------------------------------
# Invariantes globais cross-stage
# ---------------------------------------------------------------------------


class TestCrossStageInvariants:
    @pytest.mark.parametrize(
        ("validator", "build_output", "known_codes"),
        [
            (
                validate_e1_output,
                lambda: _e1_output(
                    members=[
                        _e1_member(key="Bad", full_name="", short_name="", role="ghost"),
                    ],
                    titular_key="unknown",
                ),
                E1_KNOWN_CODES,
            ),
            (
                validate_e15_output,
                lambda: _e15_minimal(
                    items=[_e15_item(code="", description="", category="exotic", year=1500)],
                    reference_year=1500,
                ),
                E15_KNOWN_CODES,
            ),
            (
                validate_e2_llm_output,
                lambda: _e2_minimal(
                    source_file="",
                    institution="",
                    transactions=[ExtractedTransaction(date="bad", description="", amount=0.0)],
                ),
                E2LLM_KNOWN_CODES,
            ),
        ],
    )
    def test_paths_jsonpath_or_none(self, validator, build_output, known_codes):
        # Todo path válido começa com $. (sub-decisão D5 ADR-165).
        for issue in validator(build_output()).issues:
            assert issue.path is None or issue.path.startswith(
                "$."
            ), f"Path inválido para {issue.code}: {issue.path!r}"

    @pytest.mark.parametrize(
        ("validator", "build_output"),
        [
            (
                validate_e1_output,
                lambda: _e1_output(members=[_e1_member(key="Bad")], titular_key="unknown"),
            ),
            (
                validate_e15_output,
                lambda: _e15_minimal(items=[], reference_year=1500),
            ),
            (
                validate_e2_llm_output,
                lambda: _e2_minimal(source_file=""),
            ),
        ],
    )
    def test_legacy_message_byte_equal_to_errors(self, validator, build_output):
        # legacy_message é byte-equal ao texto em errors/warnings (paridade onda 4).
        r = validator(build_output())
        for issue in r.issues:
            bucket = r.errors if issue.severity == "error" else r.warnings
            assert (
                issue.legacy_message in bucket
            ), f"legacy_message não está em {issue.severity}s: {issue.legacy_message!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
