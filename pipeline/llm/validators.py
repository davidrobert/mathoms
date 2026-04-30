"""Compatibility validators — ensure LLM stage outputs conform to downstream expectations."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

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


# =============================================================================
# E1.6 — IRPF full schema validator (ADR-157)
# =============================================================================
#
# Camadas:
#  1. Anti-PII: regex CPF/CNPJ não-mascarado em qualquer string field fora dos
#     campos `*_masked`/`cnpj` da fonte PJ. Match → erro abortivo (recusa payload).
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


def _scan_free_text_fields_for_pii(output: IRPFFullOutput, r: ValidationResult) -> None:
    """Anti-PII em campos livres (notes, descricao, discriminacao) — ADR-157 sub-decisão 5."""
    notes = output.notes or ""
    if _has_unmasked_cpf(notes):
        r.error("E1.6: campo 'notes' contém CPF não-mascarado (PII)")

    for i, item in enumerate(output.rendimentos_isentos):
        if _has_unmasked_cpf(item.descricao) or (item.fonte and _has_unmasked_cpf(item.fonte)):
            r.error(f"E1.6: rendimentos_isentos[{i}] contém CPF não-mascarado em campo livre")
    for i, item in enumerate(output.rendimentos_tributacao_exclusiva):
        if _has_unmasked_cpf(item.descricao):
            r.error(
                f"E1.6: rendimentos_tributacao_exclusiva[{i}] contém CPF não-mascarado em descricao"
            )
    for i, item in enumerate(output.dividas_onus):
        if _has_unmasked_cpf(item.discriminacao):
            r.error(f"E1.6: dividas_onus[{i}] contém CPF não-mascarado em discriminacao")
    for i, item in enumerate(output.bens_direitos):
        if _has_unmasked_cpf(item.descricao):
            r.error(f"E1.6: bens_direitos[{i}] contém CPF não-mascarado em descricao")


def _reconcile_ir_pago(output: IRPFFullOutput, r: ValidationResult) -> None:
    """ADR-157 sub-decisão 6: ir_pago_brl ≈ sum retidos com tolerância 0,02 BRL."""
    soma_retidos = Decimal("0")
    for fp in output.rendimentos_pj:
        soma_retidos += fp.ir_retido_brl
        if fp.decimo_terceiro_ir_retido_brl is not None:
            soma_retidos += fp.decimo_terceiro_ir_retido_brl
    for fp in output.rendimentos_pf:
        soma_retidos += fp.ir_recolhido_brl

    diff = abs(output.imposto_apurado.ir_pago_brl - soma_retidos)
    if diff > _E16_RECONCILE_TOLERANCE:
        r.warn(
            f"E1.6: ir_pago_brl ({output.imposto_apurado.ir_pago_brl}) divergente da "
            f"soma de retidos ({soma_retidos}); diff={diff} > tol={_E16_RECONCILE_TOLERANCE}. "
            f"Confidence será cap em 0.7 pelo stage runner."
        )


def _validate_imposto_xor(output: IRPFFullOutput, r: ValidationResult) -> None:
    imp = output.imposto_apurado
    a_pagar = imp.ir_a_pagar_brl or Decimal("0")
    a_restituir = imp.ir_a_restituir_brl or Decimal("0")
    if a_pagar > 0 and a_restituir > 0:
        r.error(
            f"E1.6: ir_a_pagar_brl ({a_pagar}) e ir_a_restituir_brl ({a_restituir}) "
            f"ambos > 0 — exclusivos por design"
        )


def _validate_pgbl_simplificado(output: IRPFFullOutput, r: ValidationResult) -> None:
    """G0 sign-off: simplificado não tem direito a deduzir PGBL."""
    if output.contribuinte.modelo.value != "simplificado":
        return
    for i, p in enumerate(output.pagamentos_efetuados):
        if p.codigo_rfb.value == "36" and p.valor_dedutivel_brl > 0:
            r.warn(
                f"E1.6: pagamento[{i}] PGBL com valor_dedutivel_brl={p.valor_dedutivel_brl} "
                f"em modelo simplificado — dedução não aceita pela RFB"
            )


def _validate_dependente_idade(output: IRPFFullOutput, r: ValidationResult) -> None:
    from datetime import date

    today = date.today()
    for i, dep in enumerate(output.dependentes):
        if dep.relacao.value != "filho_filha":
            continue
        if dep.data_nascimento is None:
            continue
        idade = (today - dep.data_nascimento).days // 365
        if idade > 24:
            r.warn(
                f"E1.6: dependente[{i}] '{dep.nome}' (filho) tem {idade} anos — "
                f"idade fora do limite RFB (21 ou 24 se universitário)"
            )


def _validate_confidence_and_identification(output: IRPFFullOutput, r: ValidationResult) -> None:
    if output.confidence < 0:
        r.error(f"E1.6: confidence {output.confidence} < 0")
    if output.confidence > 1:
        r.error(f"E1.6: confidence {output.confidence} > 1")
    contrib = output.contribuinte
    if contrib.exercicio < contrib.ano_base:
        r.error(f"E1.6: exercicio ({contrib.exercicio}) deve ser >= ano_base ({contrib.ano_base})")
    if contrib.exercicio > contrib.ano_base + 1:
        r.warn(
            f"E1.6: exercicio ({contrib.exercicio}) muito posterior ao "
            f"ano_base ({contrib.ano_base}) — geralmente diferem em 1"
        )


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
