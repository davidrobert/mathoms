"""Compatibility validators — ensure LLM stage outputs conform to downstream expectations.

E1 output must be consumable by config/family_members.json consumers.
E1.5 and E2-llm outputs must be consumable by E3 (reconciliation).
"""

from __future__ import annotations

import re
from typing import Any

from pipeline.llm.schemas.e1_members import MembersExtractOutput
from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput
from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput

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


class ValidationResult:
    """Accumulates validation errors and warnings."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_e1_output(output: MembersExtractOutput) -> ValidationResult:
    """Validate E1 output for compatibility with family_members.json format."""
    r = ValidationResult()

    if not output.members:
        r.error("E1: no members extracted")
        return r

    keys_seen: set[str] = set()
    for m in output.members:
        if not m.key or not m.key.islower() or " " in m.key:
            r.error(f"E1: member key must be lowercase without spaces: '{m.key}'")
        if m.key in keys_seen:
            r.error(f"E1: duplicate member key: '{m.key}'")
        keys_seen.add(m.key)

        if not m.full_name.strip():
            r.error(f"E1: member '{m.key}' has empty full_name")
        if not m.short_name.strip():
            r.error(f"E1: member '{m.key}' has empty short_name")

        if m.role not in VALID_ROLES:
            r.warn(f"E1: member '{m.key}' has unexpected role '{m.role}'")

        if m.cpf and (len(m.cpf) != 11 or not m.cpf.isdigit()):
            r.warn(f"E1: member '{m.key}' CPF should be 11 digits, got '{m.cpf}'")

        if m.birth_date and not DATE_RE.match(m.birth_date):
            r.warn(f"E1: member '{m.key}' birth_date not YYYY-MM-DD: '{m.birth_date}'")

        for acc in m.accounts:
            if not acc.institution_code:
                r.warn(f"E1: member '{m.key}' has account with empty institution_code")
            if acc.account_type not in VALID_ACCOUNT_TYPES:
                r.warn(f"E1: member '{m.key}' account type '{acc.account_type}' is non-standard")

    if output.titular_key and output.titular_key not in keys_seen:
        r.error(f"E1: titular_key '{output.titular_key}' not in extracted members")

    titular_count = sum(1 for m in output.members if m.role == "titular")
    if titular_count == 0:
        r.warn("E1: no member with role 'titular' found")
    if titular_count > 1:
        r.warn("E1: multiple members with role 'titular'")

    return r


def validate_e15_output(output: BaselinePatrimonialOutput) -> ValidationResult:
    """Validate E1.5 output for compatibility with E3 input and baseline format."""
    r = ValidationResult()

    if not output.items:
        r.warn("E1.5: no patrimonial items extracted")

    for i, item in enumerate(output.items):
        if not item.code:
            r.warn(f"E1.5: item[{i}] has empty code")
        if not item.description.strip():
            r.warn(f"E1.5: item[{i}] has empty description")
        if item.category not in VALID_CATEGORIES:
            r.warn(f"E1.5: item[{i}] category '{item.category}' is non-standard")
        if not item.member_key:
            r.error(f"E1.5: item[{i}] missing member_key")
        if item.year < 2000 or item.year > 2100:
            r.warn(f"E1.5: item[{i}] year {item.year} seems invalid")

    computed_assets = sum(i.value_brl for i in output.items if i.value_brl > 0)
    computed_liabs = sum(abs(i.value_brl) for i in output.items if i.value_brl < 0)

    if output.items and abs(computed_assets - output.total_assets_brl) > 1.0:
        r.warn(
            f"E1.5: total_assets_brl ({output.total_assets_brl}) doesn't match "
            f"sum of positive items ({computed_assets})"
        )

    if (
        output.net_worth_brl != 0
        and abs(output.net_worth_brl - (output.total_assets_brl - output.total_liabilities_brl))
        > 1.0
    ):
        r.warn("E1.5: net_worth_brl doesn't match total_assets - total_liabilities")

    if not output.reference_year or output.reference_year < 2000:
        r.error(f"E1.5: invalid reference_year: {output.reference_year}")

    return r


def validate_e2_llm_output(output: LLMExtractOutput) -> ValidationResult:
    """Validate E2-llm output for compatibility with E3 reconciliation input."""
    r = ValidationResult()

    if not output.source_file:
        r.error("E2-llm: missing source_file")
    if not output.institution:
        r.error("E2-llm: missing institution")

    if not output.transactions and not output.investments:
        r.warn("E2-llm: no transactions and no investments extracted")

    for i, t in enumerate(output.transactions):
        if not DATE_RE.match(t.date):
            r.error(f"E2-llm: transaction[{i}] date not YYYY-MM-DD: '{t.date}'")
        if not t.description.strip():
            r.warn(f"E2-llm: transaction[{i}] has empty description")
        if t.amount == 0:
            r.warn(f"E2-llm: transaction[{i}] has zero amount")

    for i, inv in enumerate(output.investments):
        if inv.type not in VALID_INVESTMENT_TYPES:
            r.warn(f"E2-llm: investment[{i}] type '{inv.type}' is non-standard")
        if not inv.institution:
            r.warn(f"E2-llm: investment[{i}] missing institution")
        if inv.value_brl <= 0:
            r.warn(f"E2-llm: investment[{i}] has non-positive value")
        if inv.applied_date and not DATE_RE.match(inv.applied_date):
            r.warn(f"E2-llm: investment[{i}] applied_date not YYYY-MM-DD")
        if inv.maturity_date and not DATE_RE.match(inv.maturity_date):
            r.warn(f"E2-llm: investment[{i}] maturity_date not YYYY-MM-DD")

    if output.period and not PERIOD_RE.match(output.period):
        r.warn(f"E2-llm: period should be YYYYMM, got '{output.period}'")

    return r
