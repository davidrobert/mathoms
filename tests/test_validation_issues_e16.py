"""ValidationIssue em E1.6 (ADR-165 onda 1) — paridade legacy + codes + context."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.schemas.e16_irpf_full import (
    CodigoPagamentoDedutivel,
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
    Contribuinte,
    Dependente,
    DividaOnusReal,
    FontePagadoraPJ,
    ImpostoApurado,
    IRPFFullOutput,
    ModeloDeclaracao,
    NaturezaContribuinte,
    PagamentoDedutivel,
    PatrimonialItem,
    RelacaoDependente,
    RendimentoIsento,
    RendimentoTribExclusiva,
)
from pipeline.llm.validators import ValidationIssue, ValidationResult, validate_e16_output

# ---------------------------------------------------------------------------
# Fixtures mínimas (replicam helpers de tests/test_irpf_full_schema_unit.py)
# ---------------------------------------------------------------------------


def _build_contribuinte(
    modelo: ModeloDeclaracao = ModeloDeclaracao.completo,
    ano_base: int = 2024,
    exercicio: int | None = None,
) -> Contribuinte:
    return Contribuinte(
        cpf_masked="***.***.***-99",
        nome="Test User",
        ano_base=ano_base,
        exercicio=exercicio if exercicio is not None else ano_base + 1,
        modelo=modelo,
        natureza=NaturezaContribuinte.titular,
    )


def _build_pj() -> FontePagadoraPJ:
    return FontePagadoraPJ(
        cnpj="**.***.***/****-**",
        nome="ACME",
        rendimentos_tributaveis_brl="150000.00",
        contrib_previdenciaria_brl="8000.00",
        ir_retido_brl="25000.00",
    )


def _build_imposto(
    ir_pago: str = "25000.00",
    ir_a_pagar: str | None = "3000.00",
    ir_a_restituir: str | None = None,
) -> ImpostoApurado:
    return ImpostoApurado(
        base_calculo_brl="130000.00",
        ir_devido_brl="28000.00",
        deducoes_totais_brl="10000.00",
        ir_pago_brl=ir_pago,
        ir_a_pagar_brl=ir_a_pagar,
        ir_a_restituir_brl=ir_a_restituir,
    )


def _minimal(
    *,
    modelo: ModeloDeclaracao = ModeloDeclaracao.completo,
    ano_base: int = 2024,
    exercicio: int | None = None,
    confidence: float = 0.95,
    ir_pago: str = "25000.00",
    ir_a_pagar: str | None = "3000.00",
    ir_a_restituir: str | None = None,
) -> IRPFFullOutput:
    return IRPFFullOutput(
        contribuinte=_build_contribuinte(modelo, ano_base, exercicio),
        rendimentos_pj=[_build_pj()],
        imposto_apurado=_build_imposto(ir_pago, ir_a_pagar, ir_a_restituir),
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# 1. Paridade byte-equal: legacy_message ≡ texto pré-migração
# ---------------------------------------------------------------------------


class TestLegacyMessageParity:
    # legacy_message deve casar byte-a-byte com o texto que a API antiga produzia
    # — _record_stage_needs_review (joins por \n) e logs continuam idênticos.

    def test_pii_notes_message(self):
        out = _minimal()
        out.notes = "CPF: 000.000.000-00 vazado"
        r = validate_e16_output(out)
        assert "E1.6: campo 'notes' contém CPF não-mascarado (PII)" in r.errors

    def test_pii_rendimentos_isentos_message(self):
        out = _minimal()
        out.rendimentos_isentos.append(
            RendimentoIsento(
                codigo_rfb=CodigoRendimentoIsento.lucros_dividendos,
                descricao="Pago para 000.000.000-00",
                valor_brl="100",
            )
        )
        r = validate_e16_output(out)
        expected = "E1.6: rendimentos_isentos[0] contém CPF não-mascarado em campo livre"
        assert expected in r.errors

    def test_pii_dividas_onus_message(self):
        """Cenário do screenshot que motivou ADR-165."""
        out = _minimal()
        out.dividas_onus.append(
            DividaOnusReal(
                codigo_rfb="11",
                discriminacao="Empréstimo de 000.000.000-00",
                valor_inicial_brl="50000.00",
                valor_final_brl="50000.00",
            )
        )
        r = validate_e16_output(out)
        expected = "E1.6: dividas_onus[0] contém CPF não-mascarado em discriminacao"
        assert expected in r.errors

    def test_imposto_xor_message(self):
        out = _minimal(ir_a_pagar="100", ir_a_restituir="100")
        r = validate_e16_output(out)
        expected = (
            "E1.6: ir_a_pagar_brl (100) e ir_a_restituir_brl (100) "
            "ambos > 0 — exclusivos por design"
        )
        assert expected in r.errors

    def test_confidence_below_zero_message(self):
        # Pydantic rejeita confidence < 0 no boundary; mutamos direto para
        # exercitar o branch defensivo do validador.
        out = _minimal()
        out.confidence = -0.5
        r = validate_e16_output(out)
        assert "E1.6: confidence -0.5 < 0" in r.errors

    def test_exercicio_anterior_ano_base_message(self):
        out = _minimal(ano_base=2024, exercicio=2023)
        r = validate_e16_output(out)
        assert "E1.6: exercicio (2023) deve ser >= ano_base (2024)" in r.errors


# ---------------------------------------------------------------------------
# 2. Issues estruturadas: code, severity, path
# ---------------------------------------------------------------------------


class TestIssuesStructure:
    def test_pii_dividas_onus_issue(self):
        out = _minimal()
        out.dividas_onus.append(
            DividaOnusReal(
                codigo_rfb="11",
                discriminacao="000.000.000-00",
                valor_inicial_brl="50000.00",
                valor_final_brl="50000.00",
            )
        )
        r = validate_e16_output(out)
        issues = [i for i in r.issues if i.code == "e16.pii.unmasked_cpf"]
        assert len(issues) == 1
        i = issues[0]
        assert i.severity == "error"
        assert i.path == "$.dividas_onus[0].discriminacao"
        assert i.context["section"] == "dividas_onus"
        assert i.context["section_label"] == "Dívidas e ônus"
        assert i.context["index"] == 0
        assert i.context["field"] == "discriminacao"

    def test_reconcile_ir_pago_issue(self):
        out = _minimal(ir_pago="99999.00")
        r = validate_e16_output(out)
        issues = [i for i in r.issues if i.code == "e16.reconcile.ir_pago_divergente"]
        assert len(issues) == 1
        i = issues[0]
        assert i.severity == "warning"
        assert i.path == "$.imposto_apurado.ir_pago_brl"
        assert i.context["ir_pago_brl"] == "99999.00"
        assert "diff_brl" in i.context

    def test_imposto_xor_issue(self):
        out = _minimal(ir_a_pagar="100", ir_a_restituir="100")
        r = validate_e16_output(out)
        issues = [i for i in r.issues if i.code == "e16.imposto.exclusivos_simultaneos"]
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].path == "$.imposto_apurado"

    def test_pgbl_simplificado_issue(self):
        out = _minimal(modelo=ModeloDeclaracao.simplificado)
        out.pagamentos_efetuados.append(
            PagamentoDedutivel(
                codigo_rfb=CodigoPagamentoDedutivel.pgbl,
                beneficiario_nome="Itau Prev",
                valor_pago_brl="10000",
                valor_dedutivel_brl="10000",
            )
        )
        r = validate_e16_output(out)
        issues = [i for i in r.issues if i.code == "e16.pgbl.deducao_em_simplificado"]
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].path == "$.pagamentos_efetuados[0]"
        assert issues[0].context["index"] == 0

    def test_dependente_idade_issue(self):
        out = _minimal()
        out.dependentes.append(
            Dependente(
                nome="Adulto",
                relacao=RelacaoDependente.filho_filha,
                data_nascimento=date(1990, 1, 1),
            )
        )
        r = validate_e16_output(out)
        issues = [i for i in r.issues if i.code == "e16.dependente.idade_acima_do_limite"]
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].path == "$.dependentes[0]"
        assert issues[0].context["nome"] == "Adulto"

    def test_confidence_out_of_range_issue(self):
        out = _minimal()
        out.confidence = -0.5
        r = validate_e16_output(out)
        issues = [i for i in r.issues if i.code == "e16.confidence.out_of_range"]
        assert len(issues) == 1
        assert issues[0].context["bound"] == "min"

    def test_exercicio_anterior_issue(self):
        out = _minimal(ano_base=2024, exercicio=2023)
        r = validate_e16_output(out)
        issues = [i for i in r.issues if i.code == "e16.contribuinte.exercicio_anterior_a_ano_base"]
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].context["exercicio"] == 2023
        assert issues[0].context["ano_base"] == 2024


# ---------------------------------------------------------------------------
# 3. Invariantes do contrato (gates ADR-165 D6)
# ---------------------------------------------------------------------------


# Codes esperados pela onda 1 — qualquer code novo em validate_e16 deve ser
# adicionado aqui. Onda 4 muda para discovery automático cross-stage.
E16_KNOWN_CODES: set[str] = {
    "e16.pii.unmasked_cpf",
    "e16.reconcile.ir_pago_divergente",
    "e16.imposto.exclusivos_simultaneos",
    "e16.pgbl.deducao_em_simplificado",
    "e16.dependente.idade_acima_do_limite",
    "e16.confidence.out_of_range",
    "e16.contribuinte.exercicio_anterior_a_ano_base",
    "e16.contribuinte.exercicio_distante_de_ano_base",
}


def _attach_pii_rendimentos(out: IRPFFullOutput) -> None:
    out.rendimentos_isentos.append(
        RendimentoIsento(
            codigo_rfb=CodigoRendimentoIsento.lucros_dividendos,
            descricao="Pago para 000.000.000-00",
            valor_brl="100",
        )
    )
    out.rendimentos_tributacao_exclusiva.append(
        RendimentoTribExclusiva(
            codigo_rfb=CodigoRendimentoTribExclusiva.jcp,
            descricao="JCP 000.000.000-00",
            valor_brl="100",
        )
    )


def _attach_pii_dividas_e_bens(out: IRPFFullOutput) -> None:
    out.dividas_onus.append(
        DividaOnusReal(
            codigo_rfb="11",
            discriminacao="000.000.000-00",
            valor_inicial_brl="100",
            valor_final_brl="100",
        )
    )
    out.bens_direitos.append(
        PatrimonialItem(
            codigo="01",
            descricao="Apto 000.000.000-00",
            categoria="imovel",
            valor_brl="500000.00",
            membro_key="t",
            ano=2024,
        )
    )


def _attach_pii_text_items(out: IRPFFullOutput) -> None:
    out.notes = "CPF 000.000.000-00"
    _attach_pii_rendimentos(out)
    _attach_pii_dividas_e_bens(out)


def _attach_pgbl_and_dependente(out: IRPFFullOutput) -> None:
    out.pagamentos_efetuados.append(
        PagamentoDedutivel(
            codigo_rfb=CodigoPagamentoDedutivel.pgbl,
            beneficiario_nome="Itau Prev",
            valor_pago_brl="10000",
            valor_dedutivel_brl="10000",
        )
    )
    out.dependentes.append(
        Dependente(
            nome="Adulto",
            relacao=RelacaoDependente.filho_filha,
            data_nascimento=date(1990, 1, 1),
        )
    )


def _build_pii_output() -> IRPFFullOutput:
    out = _minimal(
        modelo=ModeloDeclaracao.simplificado,
        ano_base=2024,
        exercicio=2023,
        ir_pago="99999.00",
        ir_a_pagar="100",
        ir_a_restituir="100",
    )
    out.confidence = -0.5
    _attach_pii_text_items(out)
    _attach_pgbl_and_dependente(out)
    return out


def _all_e16_issues() -> list[ValidationIssue]:
    return validate_e16_output(_build_pii_output()).issues


class TestContractInvariants:
    def test_all_codes_registered(self):
        # Qualquer code emitido por E1.6 está em E16_KNOWN_CODES (gate D6 ADR-165).
        emitted = {i.code for i in _all_e16_issues()}
        unknown = emitted - E16_KNOWN_CODES
        assert not unknown, f"Codes não registrados: {sorted(unknown)}"

    def test_all_paths_jsonpath(self):
        # Todo `path` ou é None ou começa com `$.` (sub-decisão D5 ADR-165).
        for issue in _all_e16_issues():
            assert issue.path is None or issue.path.startswith(
                "$."
            ), f"Path inválido para {issue.code}: {issue.path!r}"

    def test_all_issues_have_legacy_message(self):
        # `legacy_message` nunca vazio — fallback obrigatório para UI/log.
        for issue in _all_e16_issues():
            assert issue.legacy_message.strip(), f"legacy_message vazio: {issue.code}"

    def test_severity_consistent_with_errors_warnings_lists(self):
        # add_issue popula errors/warnings em sincronia com severity.
        out = _minimal(ir_a_pagar="100", ir_a_restituir="100")
        out.notes = "CPF 000.000.000-00"
        r = validate_e16_output(out)
        for issue in r.issues:
            bucket = r.errors if issue.severity == "error" else r.warnings
            assert issue.legacy_message in bucket

    def test_no_legacy_unmigrated_in_e16(self):
        # Onda 1 migra todos os ~13 sites do E1.6 — nenhum deve cair em legacy.
        for issue in _all_e16_issues():
            assert (
                issue.code != "legacy.unmigrated"
            ), f"Site não migrado em validate_e16: {issue.legacy_message!r}"


# ---------------------------------------------------------------------------
# 4. Backwards-compat: API legada continua funcionando para outros stages
# ---------------------------------------------------------------------------


class TestLegacyApiBackwardsCompat:
    # E1/E1.5/E2-llm ainda usam r.error(msg)/r.warn(msg) — emitem code=legacy.unmigrated.

    def test_error_legacy_populates_issues(self):
        r = ValidationResult()
        r.error("E1: legacy error string")
        assert r.errors == ["E1: legacy error string"]
        assert len(r.issues) == 1
        assert r.issues[0].code == "legacy.unmigrated"
        assert r.issues[0].severity == "error"
        assert r.issues[0].legacy_message == "E1: legacy error string"

    def test_warn_legacy_populates_issues(self):
        r = ValidationResult()
        r.warn("E2-llm: legacy warning")
        assert r.warnings == ["E2-llm: legacy warning"]
        assert len(r.issues) == 1
        assert r.issues[0].code == "legacy.unmigrated"
        assert r.issues[0].severity == "warning"

    def test_to_dict_includes_issues(self):
        r = ValidationResult()
        r.add_issue(
            code="e16.pii.unmasked_cpf",
            severity="error",
            path="$.notes",
            context={"field": "notes"},
            legacy_message="E1.6: campo 'notes' contém CPF não-mascarado (PII)",
        )
        d = r.to_dict()
        assert d["valid"] is False
        assert d["errors"] == ["E1.6: campo 'notes' contém CPF não-mascarado (PII)"]
        assert d["issues"][0]["code"] == "e16.pii.unmasked_cpf"
        assert d["issues"][0]["path"] == "$.notes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
