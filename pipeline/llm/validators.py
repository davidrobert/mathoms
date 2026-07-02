"""Compatibility validators — ensure LLM stage outputs conform to downstream expectations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.llm.schemas.e1_members import MembersExtractOutput
from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput
from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput
from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput

VALID_ROLES = {"titular", "conjuge", "filho", "dependente"}
VALID_ACCOUNT_TYPES = {"extratoconta", "cartao_credito", "investimento", "poupanca"}
VALID_CATEGORIES = {
    "imovel",
    "veiculo",
    "investimento",
    "conta_corrente",
    "poupanca",
    "previdencia",
    "outros",
}
VALID_INVESTMENT_TYPES = {
    "cdb",
    "lci",
    "lca",
    "fundo",
    "acao",
    "tesouro",
    "poupanca",
    "previdencia",
    "outros",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PERIOD_RE = re.compile(r"^\d{6}$")


Severity = Literal["error", "warning"]


# ADR-272 Fase 2: projeção do vocabulário ADR-165 (granular) → ReviewReasonCode
# (consultável). Lossy de propósito. offending_keys = chaves de context comprovadamente
# NÃO-monetárias a expor; None = valor monetário (omitido, pois redact_pii não mascara
# float cru "1234.56" sem confundir com confidence "0.62"/ano "2024"). code ausente aqui
# não vira ReviewReason (projetor descarta com WARNING). Fase 2 cobre só e15.*.
_REVIEW_REASON_MAP: dict[str, tuple[ReviewReasonCode, str, str, tuple[str, ...] | None]] = {
    "e15.items.empty": (
        ReviewReasonCode.extract_missing_required_field,
        "Baseline patrimonial sem itens",
        "baseline com >=1 item patrimonial",
        (),
    ),
    "e15.item.empty_code": (
        ReviewReasonCode.extract_missing_required_field,
        "Item patrimonial sem code",
        "item.code nao-vazio",
        ("index",),
    ),
    "e15.item.empty_description": (
        ReviewReasonCode.extract_missing_required_field,
        "Item patrimonial sem descricao",
        "item.description nao-vazio",
        ("index",),
    ),
    "e15.item.missing_member_key": (
        ReviewReasonCode.extract_missing_required_field,
        "Item patrimonial sem member_key",
        "item.member_key presente",
        ("index",),
    ),
    "e15.item.non_standard_category": (
        ReviewReasonCode.domain_validation_conflict,
        "Categoria de item nao-padrao",
        "category em VALID_CATEGORIES",
        ("index", "category"),
    ),
    "e15.item.invalid_year": (
        ReviewReasonCode.domain_validation_conflict,
        "Ano de item fora do intervalo",
        "2000 <= year <= 2100",
        ("index", "year"),
    ),
    "e15.totals.assets_mismatch": (
        ReviewReasonCode.domain_validation_conflict,
        "Soma de ativos diverge do total declarado",
        "soma(itens>0) == total_assets_brl",
        None,
    ),
    "e15.totals.net_worth_mismatch": (
        ReviewReasonCode.domain_validation_conflict,
        "Patrimonio liquido diverge de ativos menos passivos",
        "net_worth_brl == total_assets_brl - total_liabilities_brl",
        None,
    ),
    "e15.contribuinte.invalid_reference_year": (
        ReviewReasonCode.domain_validation_conflict,
        "Ano de referencia invalido",
        "reference_year >= 2000",
        ("reference_year",),
    ),
}


def _offending_value(context: dict[str, Any], keys: tuple[str, ...] | None) -> str:
    """offending_value seguro: só campos não-monetários; monetário (keys=None) é omitido."""
    if keys is None:
        return "(valores monetarios omitidos)"
    pairs = [f"{k}={context[k]}" for k in keys if context.get(k) is not None]
    return "; ".join(pairs) or "(sem detalhe)"


@dataclass(frozen=True)
class ValidationIssue:
    """Issue de validação estruturada (ADR-165) — code+path+context+legacy_message."""

    code: str
    severity: Severity
    path: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    legacy_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "context": self.context,
            "legacy_message": self.legacy_message,
        }

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason | None:
        """Projeta (ADR-272) para ReviewReason; None se o code não está mapeado."""
        mapped = _REVIEW_REASON_MAP.get(self.code)
        if mapped is None:
            return None
        code, message, expected, offending_keys = mapped
        return ReviewReason(
            code=code,
            stage=stage,
            artifact_key=artifact_key,
            document_id=document_id,
            offending_value=_offending_value(self.context, offending_keys),
            expected=expected,
            message=message,
        )


class ValidationResult:
    """Acumula errors/warnings (legado) + issues estruturadas (ADR-165)."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.issues: list[ValidationIssue] = []

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str) -> None:
        # [deprecated ADR-165] string livre — migrar para add_issue(code=...)
        self.add_issue(code="legacy.unmigrated", severity="error", legacy_message=msg)

    def warn(self, msg: str) -> None:
        # [deprecated ADR-165] string livre — migrar para add_issue(code=...)
        self.add_issue(code="legacy.unmigrated", severity="warning", legacy_message=msg)

    def add_issue(
        self,
        *,
        code: str,
        severity: Severity,
        legacy_message: str,
        path: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        bucket = self.errors if severity == "error" else self.warnings
        bucket.append(legacy_message)
        self.issues.append(
            ValidationIssue(
                code=code,
                severity=severity,
                path=path,
                context=dict(context or {}),
                legacy_message=legacy_message,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "issues": [i.to_dict() for i in self.issues],
        }


# Tabela code → (severity, path, base_ctx). Helper `_emit_e1` injeta extras
# do call-site via kwargs e produz issue + legacy_message juntos.
_E1_RULES: dict[str, tuple[Severity, str, dict[str, Any]]] = {
    "e1.members.empty": (
        "error",
        "$.members",
        {"section": "members", "section_label": "Membros da família"},
    ),
    "e1.member.invalid_key": (
        "error",
        "$.members[].key",
        {"section": "members", "section_label": "Membros da família", "field": "key"},
    ),
    "e1.member.duplicate_key": (
        "error",
        "$.members[].key",
        {"section": "members", "section_label": "Membros da família", "field": "key"},
    ),
    "e1.member.empty_full_name": (
        "error",
        "$.members[].full_name",
        {"section": "members", "section_label": "Membros da família", "field": "full_name"},
    ),
    "e1.member.empty_short_name": (
        "error",
        "$.members[].short_name",
        {"section": "members", "section_label": "Membros da família", "field": "short_name"},
    ),
    "e1.member.unexpected_role": (
        "warning",
        "$.members[].role",
        {"section": "members", "section_label": "Membros da família", "field": "role"},
    ),
    "e1.member.invalid_cpf": (
        "warning",
        "$.members[].cpf",
        {"section": "members", "section_label": "Membros da família", "field": "cpf"},
    ),
    "e1.member.invalid_birth_date": (
        "warning",
        "$.members[].birth_date",
        {"section": "members", "section_label": "Membros da família", "field": "birth_date"},
    ),
    "e1.account.missing_institution": (
        "warning",
        "$.members[].accounts[].institution_code",
        {
            "section": "members",
            "section_label": "Membros da família",
            "field": "institution_code",
        },
    ),
    "e1.account.non_standard_type": (
        "warning",
        "$.members[].accounts[].account_type",
        {"section": "members", "section_label": "Membros da família", "field": "account_type"},
    ),
    "e1.titular.unknown_key": (
        "error",
        "$.titular_key",
        {"section": "titular", "section_label": "Titular", "field": "titular_key"},
    ),
    "e1.titular.missing": (
        "warning",
        "$.members[].role",
        {"section": "titular", "section_label": "Titular"},
    ),
    "e1.titular.multiple": (
        "warning",
        "$.members[].role",
        {"section": "titular", "section_label": "Titular"},
    ),
}


def _emit_e1(r: ValidationResult, code: str, msg: str, **extras: Any) -> None:
    severity, path, base_ctx = _E1_RULES[code]
    r.add_issue(
        code=code,
        severity=severity,
        path=path,
        context={**base_ctx, **extras},
        legacy_message=msg,
    )


def _validate_e1_member_keys(m: Any, keys_seen: set[str], r: ValidationResult) -> None:
    if not m.key or not m.key.islower() or " " in m.key:
        _emit_e1(
            r,
            "e1.member.invalid_key",
            f"E1: member key must be lowercase without spaces: '{m.key}'",
            member_key=m.key,
        )
    if m.key in keys_seen:
        _emit_e1(
            r, "e1.member.duplicate_key", f"E1: duplicate member key: '{m.key}'", member_key=m.key
        )


def _validate_e1_member_names(m: Any, r: ValidationResult) -> None:
    if not m.full_name.strip():
        _emit_e1(
            r,
            "e1.member.empty_full_name",
            f"E1: member '{m.key}' has empty full_name",
            member_key=m.key,
        )
    if not m.short_name.strip():
        _emit_e1(
            r,
            "e1.member.empty_short_name",
            f"E1: member '{m.key}' has empty short_name",
            member_key=m.key,
        )


def _validate_e1_member_attrs(m: Any, r: ValidationResult) -> None:
    if m.role not in VALID_ROLES:
        _emit_e1(
            r,
            "e1.member.unexpected_role",
            f"E1: member '{m.key}' has unexpected role '{m.role}'",
            member_key=m.key,
            role=m.role,
        )
    if m.cpf and (len(m.cpf) != 11 or not m.cpf.isdigit()):
        _emit_e1(
            r,
            "e1.member.invalid_cpf",
            f"E1: member '{m.key}' CPF should be 11 digits, got '{m.cpf}'",
            member_key=m.key,
        )
    if m.birth_date and not DATE_RE.match(m.birth_date):
        _emit_e1(
            r,
            "e1.member.invalid_birth_date",
            f"E1: member '{m.key}' birth_date not YYYY-MM-DD: '{m.birth_date}'",
            member_key=m.key,
        )


def _validate_e1_member_accounts(m: Any, r: ValidationResult) -> None:
    for acc in m.accounts:
        if not acc.institution_code:
            _emit_e1(
                r,
                "e1.account.missing_institution",
                f"E1: member '{m.key}' has account with empty institution_code",
                member_key=m.key,
            )
        if acc.account_type not in VALID_ACCOUNT_TYPES:
            _emit_e1(
                r,
                "e1.account.non_standard_type",
                f"E1: member '{m.key}' account type '{acc.account_type}' is non-standard",
                member_key=m.key,
                account_type=acc.account_type,
            )


def _validate_e1_member(m: Any, keys_seen: set[str], r: ValidationResult) -> None:
    _validate_e1_member_keys(m, keys_seen, r)
    _validate_e1_member_names(m, r)
    _validate_e1_member_attrs(m, r)
    _validate_e1_member_accounts(m, r)


def _validate_e1_titular(output: Any, keys_seen: set[str], r: ValidationResult) -> None:
    if output.titular_key and output.titular_key not in keys_seen:
        _emit_e1(
            r,
            "e1.titular.unknown_key",
            f"E1: titular_key '{output.titular_key}' not in extracted members",
            titular_key=output.titular_key,
        )
    titular_count = sum(1 for m in output.members if m.role == "titular")
    if titular_count == 0:
        _emit_e1(r, "e1.titular.missing", "E1: no member with role 'titular' found")
    if titular_count > 1:
        _emit_e1(r, "e1.titular.multiple", "E1: multiple members with role 'titular'")


def validate_e1_output(output: MembersExtractOutput) -> ValidationResult:
    """Validate E1 output for compatibility with family_members.json format."""
    r = ValidationResult()
    if not output.members:
        _emit_e1(r, "e1.members.empty", "E1: no members extracted")
        return r
    keys_seen: set[str] = set()
    for m in output.members:
        _validate_e1_member(m, keys_seen, r)
        keys_seen.add(m.key)
    _validate_e1_titular(output, keys_seen, r)
    return r


_E15_ITEMS = {"section": "items", "section_label": "Itens patrimoniais"}
_E15_TOTALS = {"section": "totals", "section_label": "Totais patrimoniais"}
_E15_CONTRIB = {"section": "contribuinte", "section_label": "Identificação"}

_E15_RULES: dict[str, tuple[Severity, dict[str, Any]]] = {
    "e15.items.empty": ("warning", _E15_ITEMS),
    "e15.item.empty_code": ("warning", {**_E15_ITEMS, "field": "code"}),
    "e15.item.empty_description": ("warning", {**_E15_ITEMS, "field": "description"}),
    "e15.item.non_standard_category": ("warning", {**_E15_ITEMS, "field": "category"}),
    "e15.item.missing_member_key": ("error", {**_E15_ITEMS, "field": "member_key"}),
    "e15.item.invalid_year": ("warning", {**_E15_ITEMS, "field": "year"}),
    "e15.totals.assets_mismatch": ("warning", {**_E15_TOTALS, "field": "total_assets_brl"}),
    "e15.totals.net_worth_mismatch": ("warning", {**_E15_TOTALS, "field": "net_worth_brl"}),
    "e15.contribuinte.invalid_reference_year": (
        "error",
        {**_E15_CONTRIB, "field": "reference_year"},
    ),
}


def _emit_e15(r: ValidationResult, code: str, msg: str, *, path: str, **extras: Any) -> None:
    severity, base_ctx = _E15_RULES[code]
    r.add_issue(
        code=code, severity=severity, path=path, context={**base_ctx, **extras}, legacy_message=msg
    )


def _validate_e15_item_strings(i: int, item: Any, r: ValidationResult) -> None:
    if not item.code:
        _emit_e15(
            r,
            "e15.item.empty_code",
            f"E1.5: item[{i}] has empty code",
            path=f"$.items[{i}].code",
            index=i,
        )
    if not item.description.strip():
        _emit_e15(
            r,
            "e15.item.empty_description",
            f"E1.5: item[{i}] has empty description",
            path=f"$.items[{i}].description",
            index=i,
        )
    if item.category not in VALID_CATEGORIES:
        _emit_e15(
            r,
            "e15.item.non_standard_category",
            f"E1.5: item[{i}] category '{item.category}' is non-standard",
            path=f"$.items[{i}].category",
            index=i,
            category=item.category,
        )


def _validate_e15_item_required(i: int, item: Any, r: ValidationResult) -> None:
    if not item.member_key:
        _emit_e15(
            r,
            "e15.item.missing_member_key",
            f"E1.5: item[{i}] missing member_key",
            path=f"$.items[{i}].member_key",
            index=i,
        )
    if item.year < 2000 or item.year > 2100:
        _emit_e15(
            r,
            "e15.item.invalid_year",
            f"E1.5: item[{i}] year {item.year} seems invalid",
            path=f"$.items[{i}].year",
            index=i,
            year=item.year,
        )


def _validate_e15_item(i: int, item: Any, r: ValidationResult) -> None:
    _validate_e15_item_strings(i, item, r)
    _validate_e15_item_required(i, item, r)


def _emit_e15_assets_mismatch(output: Any, computed: "Decimal", r: ValidationResult) -> None:
    _emit_e15(
        r,
        "e15.totals.assets_mismatch",
        f"E1.5: total_assets_brl ({output.total_assets_brl}) doesn't match "
        f"sum of positive items ({computed})",
        path="$.total_assets_brl",
        total_assets_brl=str(output.total_assets_brl),
        computed_assets_brl=str(computed),
    )


def _validate_e15_totals(output: Any, r: ValidationResult) -> None:
    if not output.items:
        return
    computed = sum(i.value_brl for i in output.items if i.value_brl > 0)
    if abs(computed - output.total_assets_brl) > 1.0:
        _emit_e15_assets_mismatch(output, computed, r)
    nw_diff = abs(output.net_worth_brl - (output.total_assets_brl - output.total_liabilities_brl))
    if output.net_worth_brl != 0 and nw_diff > 1.0:
        _emit_e15(
            r,
            "e15.totals.net_worth_mismatch",
            "E1.5: net_worth_brl doesn't match total_assets - total_liabilities",
            path="$.net_worth_brl",
        )


def validate_e15_output(output: BaselinePatrimonialOutput) -> ValidationResult:
    """Validate E1.5 output for compatibility with E3 input and baseline format."""
    r = ValidationResult()
    if not output.items:
        _emit_e15(r, "e15.items.empty", "E1.5: no patrimonial items extracted", path="$.items")
    for i, item in enumerate(output.items):
        _validate_e15_item(i, item, r)
    _validate_e15_totals(output, r)
    if not output.reference_year or output.reference_year < 2000:
        _emit_e15(
            r,
            "e15.contribuinte.invalid_reference_year",
            f"E1.5: invalid reference_year: {output.reference_year}",
            path="$.reference_year",
            reference_year=output.reference_year,
        )
    return r


_E2LLM_TX = {"section": "transactions", "section_label": "Transações"}
_E2LLM_INV = {"section": "investments", "section_label": "Investimentos"}
_E2LLM_META = {"section": "metadata", "section_label": "Metadados"}

_E2LLM_RULES: dict[str, tuple[Severity, dict[str, Any]]] = {
    "e2llm.missing.source_file": ("error", {**_E2LLM_META, "field": "source_file"}),
    "e2llm.missing.institution": ("error", {**_E2LLM_META, "field": "institution"}),
    "e2llm.empty.no_data": ("warning", _E2LLM_META),
    "e2llm.invalid_period_format": ("warning", {**_E2LLM_META, "field": "period"}),
    "e2llm.transaction.invalid_date": ("error", {**_E2LLM_TX, "field": "date"}),
    "e2llm.transaction.empty_description": ("warning", {**_E2LLM_TX, "field": "description"}),
    "e2llm.transaction.zero_amount": ("warning", {**_E2LLM_TX, "field": "amount"}),
    "e2llm.investment.non_standard_type": ("warning", {**_E2LLM_INV, "field": "type"}),
    "e2llm.investment.missing_institution": ("warning", {**_E2LLM_INV, "field": "institution"}),
    "e2llm.investment.non_positive_value": ("warning", {**_E2LLM_INV, "field": "value_brl"}),
    "e2llm.investment.invalid_applied_date": ("warning", {**_E2LLM_INV, "field": "applied_date"}),
    "e2llm.investment.invalid_maturity_date": (
        "warning",
        {**_E2LLM_INV, "field": "maturity_date"},
    ),
}


def _emit_e2llm(r: ValidationResult, code: str, msg: str, *, path: str, **extras: Any) -> None:
    severity, base_ctx = _E2LLM_RULES[code]
    r.add_issue(
        code=code, severity=severity, path=path, context={**base_ctx, **extras}, legacy_message=msg
    )


def _validate_e2_transaction_date(i: int, t: Any, r: ValidationResult) -> None:
    if not DATE_RE.match(t.date):
        _emit_e2llm(
            r,
            "e2llm.transaction.invalid_date",
            f"E2-llm: transaction[{i}] date not YYYY-MM-DD: '{t.date}'",
            path=f"$.transactions[{i}].date",
            index=i,
            date=t.date,
        )


def _validate_e2_transaction_content(i: int, t: Any, r: ValidationResult) -> None:
    if not t.description.strip():
        _emit_e2llm(
            r,
            "e2llm.transaction.empty_description",
            f"E2-llm: transaction[{i}] has empty description",
            path=f"$.transactions[{i}].description",
            index=i,
        )
    if t.amount == 0:
        _emit_e2llm(
            r,
            "e2llm.transaction.zero_amount",
            f"E2-llm: transaction[{i}] has zero amount",
            path=f"$.transactions[{i}].amount",
            index=i,
        )


def _validate_e2_transaction(i: int, t: Any, r: ValidationResult) -> None:
    _validate_e2_transaction_date(i, t, r)
    _validate_e2_transaction_content(i, t, r)


def _validate_e2_investment_basics(i: int, inv: Any, r: ValidationResult) -> None:
    if inv.type not in VALID_INVESTMENT_TYPES:
        _emit_e2llm(
            r,
            "e2llm.investment.non_standard_type",
            f"E2-llm: investment[{i}] type '{inv.type}' is non-standard",
            path=f"$.investments[{i}].type",
            index=i,
            type_value=inv.type,
        )
    if not inv.institution:
        _emit_e2llm(
            r,
            "e2llm.investment.missing_institution",
            f"E2-llm: investment[{i}] missing institution",
            path=f"$.investments[{i}].institution",
            index=i,
        )
    if inv.value_brl <= 0:
        _emit_e2llm(
            r,
            "e2llm.investment.non_positive_value",
            f"E2-llm: investment[{i}] has non-positive value",
            path=f"$.investments[{i}].value_brl",
            index=i,
        )


def _validate_e2_investment_dates(i: int, inv: Any, r: ValidationResult) -> None:
    if inv.applied_date and not DATE_RE.match(inv.applied_date):
        _emit_e2llm(
            r,
            "e2llm.investment.invalid_applied_date",
            f"E2-llm: investment[{i}] applied_date not YYYY-MM-DD",
            path=f"$.investments[{i}].applied_date",
            index=i,
        )
    if inv.maturity_date and not DATE_RE.match(inv.maturity_date):
        _emit_e2llm(
            r,
            "e2llm.investment.invalid_maturity_date",
            f"E2-llm: investment[{i}] maturity_date not YYYY-MM-DD",
            path=f"$.investments[{i}].maturity_date",
            index=i,
        )


def _validate_e2_investment(i: int, inv: Any, r: ValidationResult) -> None:
    _validate_e2_investment_basics(i, inv, r)
    _validate_e2_investment_dates(i, inv, r)


def _validate_e2llm_required(output: Any, r: ValidationResult) -> None:
    if not output.source_file:
        _emit_e2llm(
            r, "e2llm.missing.source_file", "E2-llm: missing source_file", path="$.source_file"
        )
    if not output.institution:
        _emit_e2llm(
            r, "e2llm.missing.institution", "E2-llm: missing institution", path="$.institution"
        )


def _validate_e2llm_envelope(output: Any, r: ValidationResult) -> None:
    if not output.transactions and not output.investments:
        _emit_e2llm(
            r,
            "e2llm.empty.no_data",
            "E2-llm: no transactions and no investments extracted",
            path="$",
        )
    if output.period and not PERIOD_RE.match(output.period):
        _emit_e2llm(
            r,
            "e2llm.invalid_period_format",
            f"E2-llm: period should be YYYYMM, got '{output.period}'",
            path="$.period",
            period=output.period,
        )


def _validate_e2llm_metadata(output: Any, r: ValidationResult) -> None:
    _validate_e2llm_required(output, r)
    _validate_e2llm_envelope(output, r)


def validate_e2_llm_output(output: LLMExtractOutput) -> ValidationResult:
    """Validate E2-llm output for compatibility with E3 reconciliation input."""
    r = ValidationResult()
    _validate_e2llm_metadata(output, r)
    for i, t in enumerate(output.transactions):
        _validate_e2_transaction(i, t, r)
    for i, inv in enumerate(output.investments):
        _validate_e2_investment(i, inv, r)
    return r


# =============================================================================
# E1.6 — IRPF full schema validator (ADR-157)
# =============================================================================
#
# Camadas:
#  1. Anti-PII: regex CPF não-mascarado em qualquer string field livre
#     (notes, descricao, discriminacao, fonte). Match → warning visível no
#     StageReview (ADR-157 errata 2026-05-22). IRPF cita CPF de terceiros
#     por design (vendedor de imóvel, credor, fonte de aluguel/pensão);
#     defesa real de PII trajeta via ADR-231 (encryption-at-rest).
#  2. Reconciliação cross-field: ir_pago_brl ≈ sum retidos PJ + sum carnê-leão.
#     Tolerância 0,02 BRL (ADR-097/D5). Fora da janela → warning + pede que o
#     stage runner cap em 0,7 a confidence.
#  3. Sandtraps: aliquota XOR (a pagar / a restituir), 13º duplo, modelo
#     simplificado vs PGBL.

_CPF_LITERAL_RE = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_CPF_LITERAL_RE_LOOSE = re.compile(r"\b\d{11}\b")  # CPF sem máscara (11 dígitos)
_E16_RECONCILE_TOLERANCE = Decimal("0.02")


def _has_unmasked_cpf(text: str) -> bool:
    if _CPF_LITERAL_RE.search(text):
        return True
    # 11-dígito match: tolerar se for CNPJ-ish? CPF em PII tem exatamente 11 dígitos.
    if _CPF_LITERAL_RE_LOOSE.search(text):
        return True
    return False


def _emit_pii_cpf(
    r: ValidationResult,
    *,
    section: str,
    section_label: str,
    field_name: str,
    path: str,
    legacy_msg: str,
    index: int | None = None,
) -> None:
    ctx: dict[str, Any] = {"section": section, "section_label": section_label, "field": field_name}
    if index is not None:
        ctx["index"] = index
    r.add_issue(
        code="e16.pii.unmasked_cpf",
        severity="warning",  # ADR-157 errata 2026-05-22 (era "error")
        path=path,
        context=ctx,
        legacy_message=legacy_msg,
    )


def _scan_pii_notes(output: IRPFFullOutput, r: ValidationResult) -> None:
    if not _has_unmasked_cpf(output.notes or ""):
        return
    _emit_pii_cpf(
        r,
        section="notes",
        section_label="Notas gerais",
        field_name="notes",
        path="$.notes",
        legacy_msg="E1.6: campo 'notes' contém CPF não-mascarado (PII)",
    )


def _scan_pii_rendimentos_isentos(output: IRPFFullOutput, r: ValidationResult) -> None:
    for i, item in enumerate(output.rendimentos_isentos):
        if not (
            _has_unmasked_cpf(item.descricao) or (item.fonte and _has_unmasked_cpf(item.fonte))
        ):
            continue
        _emit_pii_cpf(
            r,
            section="rendimentos_isentos",
            section_label="Rendimentos isentos",
            field_name="descricao_or_fonte",
            path=f"$.rendimentos_isentos[{i}]",
            index=i,
            legacy_msg=f"E1.6: rendimentos_isentos[{i}] contém CPF não-mascarado em campo livre",
        )


def _scan_pii_rendimentos_tributacao_exclusiva(output: IRPFFullOutput, r: ValidationResult) -> None:
    for i, item in enumerate(output.rendimentos_tributacao_exclusiva):
        if not _has_unmasked_cpf(item.descricao):
            continue
        _emit_pii_cpf(
            r,
            section="rendimentos_tributacao_exclusiva",
            section_label="Rendimentos com tributação exclusiva",
            field_name="descricao",
            path=f"$.rendimentos_tributacao_exclusiva[{i}].descricao",
            index=i,
            legacy_msg=(
                f"E1.6: rendimentos_tributacao_exclusiva[{i}] contém CPF não-mascarado em descricao"
            ),
        )


def _scan_pii_dividas_onus(output: IRPFFullOutput, r: ValidationResult) -> None:
    for i, item in enumerate(output.dividas_onus):
        if not _has_unmasked_cpf(item.discriminacao):
            continue
        _emit_pii_cpf(
            r,
            section="dividas_onus",
            section_label="Dívidas e ônus",
            field_name="discriminacao",
            path=f"$.dividas_onus[{i}].discriminacao",
            index=i,
            legacy_msg=f"E1.6: dividas_onus[{i}] contém CPF não-mascarado em discriminacao",
        )


def _scan_pii_bens_direitos(output: IRPFFullOutput, r: ValidationResult) -> None:
    for i, item in enumerate(output.bens_direitos):
        if not _has_unmasked_cpf(item.descricao):
            continue
        _emit_pii_cpf(
            r,
            section="bens_direitos",
            section_label="Bens e direitos",
            field_name="descricao",
            path=f"$.bens_direitos[{i}].descricao",
            index=i,
            legacy_msg=f"E1.6: bens_direitos[{i}] contém CPF não-mascarado em descricao",
        )


def _scan_free_text_fields_for_pii(output: IRPFFullOutput, r: ValidationResult) -> None:
    """Anti-PII em campos livres (ADR-157 D5) — colapsa em e16.pii.unmasked_cpf."""
    _scan_pii_notes(output, r)
    _scan_pii_rendimentos_isentos(output, r)
    _scan_pii_rendimentos_tributacao_exclusiva(output, r)
    _scan_pii_dividas_onus(output, r)
    _scan_pii_bens_direitos(output, r)


def _soma_retidos_irpf(output: IRPFFullOutput) -> Decimal:
    soma = Decimal("0")
    for fp in output.rendimentos_pj:
        soma += fp.ir_retido_brl
        if fp.decimo_terceiro_ir_retido_brl is not None:
            soma += fp.decimo_terceiro_ir_retido_brl
    for fp in output.rendimentos_pf:
        soma += fp.ir_recolhido_brl
    return soma


_RECONCILE_BASE_CTX = {
    "section": "imposto_apurado",
    "section_label": "Imposto apurado",
    "field": "ir_pago_brl",
}


def _emit_reconcile_div(
    r: ValidationResult, ir_pago: Decimal, soma: Decimal, diff: Decimal
) -> None:
    tol = _E16_RECONCILE_TOLERANCE
    r.add_issue(
        code="e16.reconcile.ir_pago_divergente",
        severity="warning",
        path="$.imposto_apurado.ir_pago_brl",
        context={
            **_RECONCILE_BASE_CTX,
            "ir_pago_brl": str(ir_pago),
            "soma_retidos_brl": str(soma),
            "diff_brl": str(diff),
            "tolerance_brl": str(tol),
        },
        legacy_message=(
            f"E1.6: ir_pago_brl ({ir_pago}) divergente da soma de retidos ({soma}); "
            f"diff={diff} > tol={tol}. Confidence será cap em 0.7 pelo stage runner."
        ),
    )


def _reconcile_ir_pago(output: IRPFFullOutput, r: ValidationResult) -> None:
    """ADR-157 sub-decisão 6: ir_pago_brl ≈ sum retidos com tolerância 0,02 BRL."""
    soma = _soma_retidos_irpf(output)
    ir_pago = output.imposto_apurado.ir_pago_brl
    diff = abs(ir_pago - soma)
    if diff > _E16_RECONCILE_TOLERANCE:
        _emit_reconcile_div(r, ir_pago, soma, diff)


def _emit_imposto_xor(r: ValidationResult, a_pagar: Decimal, a_restituir: Decimal) -> None:
    r.add_issue(
        code="e16.imposto.exclusivos_simultaneos",
        severity="error",
        path="$.imposto_apurado",
        context={
            "section": "imposto_apurado",
            "section_label": "Imposto apurado",
            "ir_a_pagar_brl": str(a_pagar),
            "ir_a_restituir_brl": str(a_restituir),
        },
        legacy_message=(
            f"E1.6: ir_a_pagar_brl ({a_pagar}) e ir_a_restituir_brl ({a_restituir}) "
            f"ambos > 0 — exclusivos por design"
        ),
    )


def _validate_imposto_xor(output: IRPFFullOutput, r: ValidationResult) -> None:
    imp = output.imposto_apurado
    a_pagar = imp.ir_a_pagar_brl or Decimal("0")
    a_restituir = imp.ir_a_restituir_brl or Decimal("0")
    if a_pagar > 0 and a_restituir > 0:
        _emit_imposto_xor(r, a_pagar, a_restituir)


def _emit_pgbl_simplificado(r: ValidationResult, i: int, valor: Decimal) -> None:
    r.add_issue(
        code="e16.pgbl.deducao_em_simplificado",
        severity="warning",
        path=f"$.pagamentos_efetuados[{i}]",
        context={
            "section": "pagamentos_efetuados",
            "section_label": "Pagamentos efetuados (PGBL)",
            "index": i,
            "valor_dedutivel_brl": str(valor),
        },
        legacy_message=(
            f"E1.6: pagamento[{i}] PGBL com valor_dedutivel_brl={valor} "
            f"em modelo simplificado — dedução não aceita pela RFB"
        ),
    )


def _validate_pgbl_simplificado(output: IRPFFullOutput, r: ValidationResult) -> None:
    """G0 sign-off: simplificado não tem direito a deduzir PGBL."""
    if output.contribuinte.modelo.value != "simplificado":
        return
    for i, p in enumerate(output.pagamentos_efetuados):
        if p.codigo_rfb.value == "36" and p.valor_dedutivel_brl > 0:
            _emit_pgbl_simplificado(r, i, p.valor_dedutivel_brl)


def _emit_dependente_idade(r: ValidationResult, i: int, nome: str, idade: int) -> None:
    r.add_issue(
        code="e16.dependente.idade_acima_do_limite",
        severity="warning",
        path=f"$.dependentes[{i}]",
        context={
            "section": "dependentes",
            "section_label": "Dependentes",
            "index": i,
            "nome": nome,
            "idade": idade,
        },
        legacy_message=(
            f"E1.6: dependente[{i}] '{nome}' (filho) tem {idade} anos — "
            f"idade fora do limite RFB (21 ou 24 se universitário)"
        ),
    )


def _validate_dependente_idade(output: IRPFFullOutput, r: ValidationResult) -> None:
    from datetime import date

    today = date.today()
    for i, dep in enumerate(output.dependentes):
        if dep.relacao.value != "filho_filha" or dep.data_nascimento is None:
            continue
        idade = (today - dep.data_nascimento).days // 365
        if idade > 24:
            _emit_dependente_idade(r, i, dep.nome, idade)


_CONFIDENCE_BASE_CTX = {
    "section": "identification",
    "section_label": "Identificação",
    "field": "confidence",
}


def _emit_confidence_oor(r: ValidationResult, c: float, *, bound: str, expected: int) -> None:
    op = "<" if bound == "min" else ">"
    r.add_issue(
        code="e16.confidence.out_of_range",
        severity="error",
        path="$.confidence",
        context={
            **_CONFIDENCE_BASE_CTX,
            "confidence": c,
            "bound": bound,
            f"expected_{bound}": expected,
        },
        legacy_message=f"E1.6: confidence {c} {op} {expected}",
    )


def _validate_confidence_range(output: IRPFFullOutput, r: ValidationResult) -> None:
    c = output.confidence
    if c < 0:
        _emit_confidence_oor(r, c, bound="min", expected=0)
    if c > 1:
        _emit_confidence_oor(r, c, bound="max", expected=1)


_EXERCICIO_BASE_CTX = {
    "section": "contribuinte",
    "section_label": "Contribuinte",
    "field": "exercicio",
}


def _emit_exercicio_anterior(r: ValidationResult, e: int, a: int) -> None:
    r.add_issue(
        code="e16.contribuinte.exercicio_anterior_a_ano_base",
        severity="error",
        path="$.contribuinte.exercicio",
        context={**_EXERCICIO_BASE_CTX, "exercicio": e, "ano_base": a},
        legacy_message=f"E1.6: exercicio ({e}) deve ser >= ano_base ({a})",
    )


def _emit_exercicio_distante(r: ValidationResult, e: int, a: int) -> None:
    r.add_issue(
        code="e16.contribuinte.exercicio_distante_de_ano_base",
        severity="warning",
        path="$.contribuinte.exercicio",
        context={**_EXERCICIO_BASE_CTX, "exercicio": e, "ano_base": a},
        legacy_message=(
            f"E1.6: exercicio ({e}) muito posterior ao ano_base ({a}) — geralmente diferem em 1"
        ),
    )


def _validate_exercicio_vs_ano_base(output: IRPFFullOutput, r: ValidationResult) -> None:
    e, a = output.contribuinte.exercicio, output.contribuinte.ano_base
    if e < a:
        _emit_exercicio_anterior(r, e, a)
    if e > a + 1:
        _emit_exercicio_distante(r, e, a)


def _validate_confidence_and_identification(output: IRPFFullOutput, r: ValidationResult) -> None:
    _validate_confidence_range(output, r)
    _validate_exercicio_vs_ano_base(output, r)


def validate_e16_output(output: IRPFFullOutput) -> ValidationResult:
    """Valida E1.6 — anti-PII em campos livres + reconciliação + sandtraps (ADR-157)."""
    r = ValidationResult()
    _validate_confidence_and_identification(output, r)
    _scan_free_text_fields_for_pii(output, r)
    _reconcile_ir_pago(output, r)
    _validate_imposto_xor(output, r)
    _validate_pgbl_simplificado(output, r)
    _validate_dependente_idade(output, r)
    return r
