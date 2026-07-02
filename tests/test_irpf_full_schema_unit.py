"""Unit tests for E1.6 (extract_irpf_full) schema, validator and analyzer (ADR-157)."""

from __future__ import annotations

import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer, partition_irpf_payloads
from pipeline.llm.schemas.e16_irpf_full import (
    PROMPT_VERSION,
    CodigoPagamentoDedutivel,
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
    Contribuinte,
    Dependente,
    FontePagadoraPF,
    FontePagadoraPJ,
    ImpostoApurado,
    IRPFFullOutput,
    ModeloDeclaracao,
    NaturezaContribuinte,
    PagamentoDedutivel,
    PatrimonialItem,
    RelacaoDependente,
    RendimentoExterior,
    RendimentoIsento,
    RendimentoTribExclusiva,
    detect_pj_suffix,
)
from pipeline.llm.validators import validate_e16_output


def _build_contribuinte(modelo: ModeloDeclaracao, ano_base: int) -> Contribuinte:
    return Contribuinte(
        cpf_masked="***.***.***-99",
        nome="Test User",
        ano_base=ano_base,
        exercicio=ano_base + 1,
        modelo=modelo,
        natureza=NaturezaContribuinte.titular,
    )


def _build_pj(rendimentos: str, ir_retido: str) -> FontePagadoraPJ:
    return FontePagadoraPJ(
        cnpj="**.***.***/****-**",
        nome="ACME",
        rendimentos_tributaveis_brl=rendimentos,
        contrib_previdenciaria_brl="8000.00",
        ir_retido_brl=ir_retido,
    )


def _build_imposto(ir_pago: str) -> ImpostoApurado:
    return ImpostoApurado(
        base_calculo_brl="130000.00",
        ir_devido_brl="28000.00",
        deducoes_totais_brl="10000.00",
        ir_pago_brl=ir_pago,
        ir_a_pagar_brl="3000.00",
    )


def _build_minimal(
    *,
    modelo: ModeloDeclaracao = ModeloDeclaracao.completo,
    ano_base: int = 2024,
    rendimentos_pj_value: str = "150000.00",
    ir_retido: str = "25000.00",
    ir_pago: str = "25000.00",
) -> IRPFFullOutput:
    return IRPFFullOutput(
        contribuinte=_build_contribuinte(modelo, ano_base),
        rendimentos_pj=[_build_pj(rendimentos_pj_value, ir_retido)],
        imposto_apurado=_build_imposto(ir_pago),
        confidence=0.95,
    )


class TestSchemaSerialization:
    def test_decimal_serializes_to_string(self):
        out = _build_minimal()
        d = out.model_dump(mode="json")
        assert isinstance(d["rendimentos_pj"][0]["rendimentos_tributaveis_brl"], str)
        assert d["rendimentos_pj"][0]["rendimentos_tributaveis_brl"] == "150000.00"

    def test_float_rejected_in_money_field(self):
        with pytest.raises(TypeError, match="float"):
            FontePagadoraPJ(
                cnpj="**.***.***/****-**",
                nome="X",
                rendimentos_tributaveis_brl=1.5,
                contrib_previdenciaria_brl="0",
                ir_retido_brl="0",
            )

    def test_unmasked_cpf_rejected_in_cpf_masked_field(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Contribuinte(
                cpf_masked="000.000.000-00",
                nome="X",
                ano_base=2024,
                exercicio=2025,
                modelo=ModeloDeclaracao.completo,
                natureza=NaturezaContribuinte.titular,
            )

    def test_top_level_lenient_accepts_unknown_field(self):
        from pydantic import ValidationError

        out = _build_minimal()
        d = out.model_dump(mode="json")
        d["future_field_2026"] = "experimental"
        # Top-level deve aceitar (extra='allow')
        IRPFFullOutput.model_validate(d)

        # Sub-model deve rejeitar (extra='forbid')
        d_bad = {
            "contribuinte": {**d["contribuinte"], "extra_garbage": 1},
            **{k: v for k, v in d.items() if k != "contribuinte"},
        }
        with pytest.raises(ValidationError):
            IRPFFullOutput.model_validate(d_bad)

    def test_prompt_version_constant(self):
        assert re.fullmatch(r"\d+\.\d+\.\d+", PROMPT_VERSION)  # semver puro pós-A20.l12

    def test_contribuinte_endereco_optional_default_none(self):
        c = _build_contribuinte(ModeloDeclaracao.completo, 2024)
        assert c.endereco is None

    def test_contribuinte_endereco_accepts_string(self):
        c = Contribuinte(
            cpf_masked="***.***.***-99",
            nome="Test User",
            ano_base=2024,
            exercicio=2025,
            modelo=ModeloDeclaracao.completo,
            natureza=NaturezaContribuinte.titular,
            endereco="Rua Exemplo, 100, Sao Paulo-SP",
        )
        assert c.endereco == "Rua Exemplo, 100, Sao Paulo-SP"

    def test_contribuinte_endereco_rejects_empty_string(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Contribuinte(
                cpf_masked="***.***.***-99",
                nome="Test User",
                ano_base=2024,
                exercicio=2025,
                modelo=ModeloDeclaracao.completo,
                natureza=NaturezaContribuinte.titular,
                endereco="",
            )


class TestValidatorAntiPii:
    # ADR-157 errata 2026-05-22: CPF em campo livre é warning, não erro abortivo.
    # IRPF cita CPF de terceiros por design (vendedor, credor, fonte de aluguel).

    def test_unmasked_cpf_in_notes_warns(self):
        out = _build_minimal()
        out.notes = "CPF: 000.000.000-00 vazado"
        r = validate_e16_output(out)
        assert any("notes" in w and "CPF" in w for w in r.warnings)
        assert r.valid, "CPF em campo livre não deve invalidar payload IRPF"

    def test_unmasked_cpf_in_descricao_warns(self):
        out = _build_minimal()
        out.rendimentos_isentos.append(
            RendimentoIsento(
                codigo_rfb=CodigoRendimentoIsento.lucros_dividendos,
                descricao="Pago para 000.000.000-00",
                valor_brl="100",
            )
        )
        r = validate_e16_output(out)
        assert any("rendimentos_isentos" in w for w in r.warnings)
        assert r.valid


class TestValidatorReconcile:
    def test_ir_pago_diverge_warning(self):
        out = _build_minimal(ir_retido="25000.00", ir_pago="99999.00")
        r = validate_e16_output(out)
        assert any("divergente" in w for w in r.warnings)

    def test_ir_pago_matches_no_warning(self):
        out = _build_minimal(ir_retido="25000.00", ir_pago="25000.00")
        r = validate_e16_output(out)
        assert not any("divergente" in w for w in r.warnings)


class TestValidatorXorImposto:
    def test_a_pagar_and_a_restituir_both_positive_rejected(self):
        out = _build_minimal()
        out.imposto_apurado.ir_a_pagar_brl = Decimal("100")
        out.imposto_apurado.ir_a_restituir_brl = Decimal("100")
        r = validate_e16_output(out)
        assert any("exclusivos" in e for e in r.errors)


class TestValidatorPgblSimplificado:
    def test_simplificado_with_pgbl_warns(self):
        out = _build_minimal(modelo=ModeloDeclaracao.simplificado)
        out.pagamentos_efetuados.append(
            PagamentoDedutivel(
                codigo_rfb=CodigoPagamentoDedutivel.pgbl,
                beneficiario_nome="Itau Prev",
                valor_pago_brl="10000",
                valor_dedutivel_brl="10000",
            )
        )
        r = validate_e16_output(out)
        assert any("simplificado" in w for w in r.warnings)


class TestValidatorDependenteIdade:
    def test_filho_acima_24_warns(self):
        out = _build_minimal()
        out.dependentes.append(
            Dependente(
                nome="Adulto",
                relacao=RelacaoDependente.filho_filha,
                data_nascimento=date(1990, 1, 1),
            )
        )
        r = validate_e16_output(out)
        assert any("idade fora" in w for w in r.warnings)


class TestIRPFAnalyzer:
    def test_empty_returns_zeros(self):
        a = IRPFAnalyzer([])
        assert a.renda_anual_familiar(2024) == Decimal("0")
        assert a.ir_pago_total(2024) == Decimal("0")
        assert a.evolucao_renda_anos() == {}

    def test_renda_anual_sum_tributavel_isento_exclusiva(self):
        decl = _build_minimal()
        decl.rendimentos_isentos.append(
            RendimentoIsento(
                codigo_rfb=CodigoRendimentoIsento.lucros_dividendos,
                descricao="Dividendos",
                valor_brl="20000.00",
            )
        )
        decl.rendimentos_tributacao_exclusiva.append(
            RendimentoTribExclusiva(
                codigo_rfb=CodigoRendimentoTribExclusiva.jcp,
                descricao="JCP",
                valor_brl="5000.00",
            )
        )
        a = IRPFAnalyzer([decl])
        # 150k tributável + 20k isento + 5k exclusiva = 175k
        assert a.renda_anual_familiar(2024) == Decimal("175000.00")

    def test_aliquotas_dual(self):
        decl = _build_minimal(
            rendimentos_pj_value="200000.00", ir_retido="35000.00", ir_pago="35000.00"
        )
        decl.rendimentos_isentos.append(
            RendimentoIsento(
                codigo_rfb=CodigoRendimentoIsento.lucros_dividendos,
                descricao="Dividendos",
                valor_brl="20000.00",
            )
        )
        a = IRPFAnalyzer([decl])
        ali = a.aliquotas(2024)
        # 35k / 200k = 17.5%; 35k / 220k = 15.909...%
        assert ali.sobre_tributavel_pct == Decimal("17.5")
        assert round(ali.sobre_total_pct, 2) == Decimal("15.91")

    def test_pgbl_capacidade_completo(self):
        decl = _build_minimal(rendimentos_pj_value="200000.00")
        decl.pagamentos_efetuados.append(
            PagamentoDedutivel(
                codigo_rfb=CodigoPagamentoDedutivel.pgbl,
                beneficiario_nome="Itau Prev",
                valor_pago_brl="10000",
                valor_dedutivel_brl="10000",
            )
        )
        a = IRPFAnalyzer([decl])
        # 12% × 200k - 10k = 14k
        assert a.pgbl_capacidade_dedutivel(2024) == Decimal("14000.00")

    def test_pgbl_capacidade_simplificado_zero(self):
        decl = _build_minimal(
            modelo=ModeloDeclaracao.simplificado, rendimentos_pj_value="200000.00"
        )
        a = IRPFAnalyzer([decl])
        assert a.pgbl_capacidade_dedutivel(2024) == Decimal("0")

    def test_split_trabalho_capital(self):
        decl = _build_minimal(rendimentos_pj_value="200000.00")
        decl.rendimentos_isentos.append(
            RendimentoIsento(
                codigo_rfb=CodigoRendimentoIsento.lucros_dividendos,
                descricao="Div",
                valor_brl="20000.00",
            )
        )
        decl.rendimentos_tributacao_exclusiva.append(
            RendimentoTribExclusiva(
                codigo_rfb=CodigoRendimentoTribExclusiva.decimo_terceiro,
                descricao="13o",
                valor_brl="15000.00",
            )
        )
        sp = IRPFAnalyzer([decl]).split_trabalho_vs_capital(2024)
        # trabalho = PJ 200k + 13o 15k = 215k; capital = lucros 20k
        assert sp.trabalho_brl == Decimal("215000.00")
        assert sp.capital_brl == Decimal("20000.00")

    def test_evolucao_renda_multi_anos(self):
        d2023 = _build_minimal(ano_base=2023, rendimentos_pj_value="100000.00")
        d2024 = _build_minimal(ano_base=2024, rendimentos_pj_value="150000.00")
        a = IRPFAnalyzer([d2023, d2024])
        ev = a.evolucao_renda_anos()
        assert ev[2023] == Decimal("100000.00")
        assert ev[2024] == Decimal("150000.00")

    def test_renda_liquida_descontando_ir_prev_pensao(self):
        decl = _build_minimal(
            rendimentos_pj_value="100000.00", ir_retido="20000.00", ir_pago="20000.00"
        )
        decl.pagamentos_efetuados.append(
            PagamentoDedutivel(
                codigo_rfb=CodigoPagamentoDedutivel.pensao_alimenticia_judicial,
                beneficiario_nome="Ex Filho",
                valor_pago_brl="12000.00",
                valor_dedutivel_brl="12000.00",
            )
        )
        a = IRPFAnalyzer([decl])
        # 100k - 20k IR - 8k prev - 12k pensão = 60k
        assert a.renda_liquida_familiar(2024) == Decimal("60000.00")

    def test_from_payloads_roundtrip(self):
        decl = _build_minimal()
        payload = decl.model_dump(mode="json")
        a = IRPFAnalyzer.from_payloads([payload])
        assert a.renda_anual_familiar(2024) == Decimal("150000.00")


class TestPatrimonialItemDecimal:
    def test_patrimonial_item_uses_decimal(self):
        item = PatrimonialItem(
            codigo="01",
            descricao="Apto",
            categoria="imovel",
            valor_brl="500000.00",
            membro_key="david",
            ano=2024,
        )
        assert isinstance(item.valor_brl, Decimal)
        with pytest.raises(TypeError):
            PatrimonialItem(
                codigo="01",
                descricao="Apto",
                categoria="imovel",
                valor_brl=500000.0,
                membro_key="david",
                ano=2024,
            )


class TestContribuintePfVsPjFilter:
    """ADR-268 (rev): ``detect_pj_suffix`` é guardrail pós-LLM, NÃO validator de
    schema que raise — documento PJ não dispara retry (ADR-238) nem bricka read."""

    def _build(self, nome: str) -> Contribuinte:
        return Contribuinte(
            cpf_masked="***.***.***-99",
            nome=nome,
            ano_base=2024,
            exercicio=2025,
            modelo=ModeloDeclaracao.completo,
            natureza=NaturezaContribuinte.titular,
        )

    def test_pf_legitimate_not_detected(self):
        assert detect_pj_suffix("Pessoa Física Exemplo") is None

    def test_construction_never_raises_on_pj(self):
        """O modelo SEMPRE desserializa — guard moveu para fora do schema."""
        c = self._build("Empresa Exemplo LTDA")
        assert c.nome == "Empresa Exemplo LTDA"

    def test_ltda_detected(self):
        assert detect_pj_suffix("Empresa Exemplo LTDA") == "LTDA"

    def test_sa_detected(self):
        assert detect_pj_suffix("Empresa Exemplo S.A.") is not None

    def test_sa_no_dots_detected(self):
        assert detect_pj_suffix("Empresa Exemplo SA") is not None

    def test_eireli_detected(self):
        assert detect_pj_suffix("Exemplo EIRELI") is not None

    def test_mei_detected(self):
        assert detect_pj_suffix("Exemplo MEI") is not None

    def test_me_detected(self):
        assert detect_pj_suffix("Exemplo Comércio ME") is not None

    def test_epp_detected(self):
        assert detect_pj_suffix("Exemplo EPP") is not None

    def test_sociedade_detected(self):
        assert detect_pj_suffix("Pessoa Sociedade Civil") is not None

    def test_associacao_detected_with_accent(self):
        assert detect_pj_suffix("Pessoa Associação Brasileira") is not None

    def test_associacao_detected_without_accent(self):
        assert detect_pj_suffix("Pessoa Associacao Brasileira") is not None

    def test_fundacao_detected(self):
        assert detect_pj_suffix("Pessoa Fundação Exemplo") is not None

    def test_cooperativa_detected(self):
        assert detect_pj_suffix("Pessoa Cooperativa Brasileira") is not None

    def test_word_boundary_eme_not_detected(self):
        """'EME' termina em ME mas é palavra inteira — `\\bME\\b` não casa."""
        assert detect_pj_suffix("Fernanda Eme Silva") is None

    def test_word_boundary_sara_not_detected(self):
        assert detect_pj_suffix("Sara Silva") is None

    def test_real_world_david_ltda_detected(self):
        """Caso real do workspace founder dogfood — sinaliza PJ, não raise."""
        assert detect_pj_suffix("David Robert Camargo de Campos LTDA") == "LTDA"

    def test_case_insensitive(self):
        assert detect_pj_suffix("exemplo ltda") is not None

    def test_none_and_empty(self):
        assert detect_pj_suffix(None) is None
        assert detect_pj_suffix("") is None


class TestPartitionIrpfPayloads:
    """ADR-268 (rev): read boundary E5 pula PJ + schema-inválido sem derrubar o
    stage — incidente 5@5.com (analyze_finances abortou em 1 artifact PJ)."""

    def _pf_payload(self, ano_base: int = 2024) -> dict:
        return _build_minimal(ano_base=ano_base).model_dump(mode="json")

    def _pj_payload(self) -> dict:
        p = self._pf_payload()
        p["contribuinte"]["nome"] = "David Robert Camargo de Campos LTDA"
        return p

    def test_pj_payload_deserializes_without_raise(self):
        """Regressão direta do crash: o payload PJ persistido reparseia OK."""
        IRPFFullOutput.model_validate(self._pj_payload())

    def test_pj_excluded_valid_kept(self):
        payloads = [self._pf_payload(2023), self._pj_payload(), self._pf_payload(2024)]
        keys = ["pf_2023", "pj_ltda", "pf_2024"]
        valid_p, valid_k, skipped = partition_irpf_payloads(payloads, keys)
        assert valid_k == ["pf_2023", "pf_2024"]
        assert skipped == [("pj_ltda", "pj_contribuinte")]
        assert len(valid_p) == 2

    def test_invalid_schema_excluded(self):
        valid_p, valid_k, skipped = partition_irpf_payloads(
            [self._pf_payload(), {"contribuinte": {"nome": "X"}}],
            ["good", "broken"],
        )
        assert valid_k == ["good"]
        assert skipped == [("broken", "invalid_schema")]

    def test_analyzer_survives_pj_via_partition(self):
        """1 PJ não derruba a análise — os anos válidos sobrevivem."""
        payloads = [self._pf_payload(2024), self._pj_payload()]
        valid_p, valid_k, _ = partition_irpf_payloads(payloads, ["pf", "pj"])
        analyzer = IRPFAnalyzer.from_payloads(valid_p, tie_break_keys=valid_k)
        assert analyzer.anos_base_disponiveis() == [2024]
