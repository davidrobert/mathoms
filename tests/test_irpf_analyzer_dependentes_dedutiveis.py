"""Unit tests for ADR-194 — IRPFAnalyzer.dependentes_count + dedutiveis_aplicados."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.irpf_analyzer import (
    EDUCACAO_TETO_PER_PESSOA,
    IRPFAnalyzer,
)
from pipeline.llm.schemas.e16_irpf_full import (
    CodigoPagamentoDedutivel,
    Contribuinte,
    Dependente,
    FontePagadoraPJ,
    ImpostoApurado,
    IRPFFullOutput,
    ModeloDeclaracao,
    NaturezaContribuinte,
    PagamentoDedutivel,
    RelacaoDependente,
)


def _contrib(ano: int = 2024) -> Contribuinte:
    return Contribuinte(
        cpf_masked="***.***.***-99",
        nome="Test User",
        ano_base=ano,
        exercicio=ano + 1,
        modelo=ModeloDeclaracao.completo,
        natureza=NaturezaContribuinte.titular,
    )


_ZERO_IMPOSTO = dict(
    base_calculo_brl="0",
    ir_devido_brl="0",
    deducoes_totais_brl="0",
    ir_pago_brl="0",
    ir_a_pagar_brl="0",
)


def _dep(relacao: RelacaoDependente, nome: str = "Dep") -> Dependente:
    return Dependente(nome=nome, relacao=relacao)


def _pagamento(
    codigo: CodigoPagamentoDedutivel,
    valor: str,
    teto_aplicado: bool = False,
) -> PagamentoDedutivel:
    return PagamentoDedutivel(
        codigo_rfb=codigo,
        beneficiario_nome="Beneficiario",
        valor_pago_brl=valor,
        valor_dedutivel_brl=valor,
        teto_aplicado=teto_aplicado,
    )


def _decl_with_3_variantes_pensao() -> IRPFFullOutput:
    decl = _decl_empty()
    P = CodigoPagamentoDedutivel
    decl.pagamentos_efetuados.extend(
        [
            _pagamento(P.pensao_alimenticia_judicial, "10000.00"),
            _pagamento(P.pensao_alimenticia_acordo_extrajudicial, "5000.00"),
            _pagamento(P.pensao_alimenticia_escritura, "2500.00"),
        ]
    )
    return decl


def _decl_empty(ano: int = 2024) -> IRPFFullOutput:
    return IRPFFullOutput(
        contribuinte=_contrib(ano),
        rendimentos_pj=[
            FontePagadoraPJ(
                cnpj="**.***.***/****-**",
                nome="ACME",
                rendimentos_tributaveis_brl="100000.00",
                contrib_previdenciaria_brl="0",
                ir_retido_brl="0",
            )
        ],
        imposto_apurado=ImpostoApurado(**_ZERO_IMPOSTO),
        confidence=0.95,
    )


# =============================================================================
# dependentes_count
# =============================================================================


class TestDependentesCount:
    def test_zero_dependentes_retorna_count_zero_e_dict_vazio(self):
        a = IRPFAnalyzer([_decl_empty()])
        out = a.dependentes_count(2024)
        assert out == {"count": 0, "por_relacao": {}}

    def test_sem_declaracao_no_ano_retorna_zero(self):
        a = IRPFAnalyzer([])
        out = a.dependentes_count(2024)
        assert out == {"count": 0, "por_relacao": {}}

    def test_um_dependente_filho(self):
        decl = _decl_empty()
        decl.dependentes.append(_dep(RelacaoDependente.filho_filha, "Filho"))
        a = IRPFAnalyzer([decl])
        out = a.dependentes_count(2024)
        assert out == {"count": 1, "por_relacao": {"filho_filha": 1}}

    def test_multiplas_relacoes_agrega_por_categoria(self):
        decl = _decl_empty()
        decl.dependentes.extend(
            [
                _dep(RelacaoDependente.conjuge_companheiro, "Cônjuge"),
                _dep(RelacaoDependente.filho_filha, "Filho 1"),
                _dep(RelacaoDependente.filho_filha, "Filho 2"),
                _dep(RelacaoDependente.pai_mae, "Mãe"),
            ]
        )
        a = IRPFAnalyzer([decl])
        out = a.dependentes_count(2024)
        assert out["count"] == 4
        assert out["por_relacao"] == {
            "conjuge_companheiro": 1,
            "filho_filha": 2,
            "pai_mae": 1,
        }

    def test_casal_com_dependentes_em_ambas_declaracoes(self):
        d1 = _decl_empty()
        d1.dependentes.append(_dep(RelacaoDependente.filho_filha, "Filho 1"))
        d2 = _decl_empty()
        d2.contribuinte = Contribuinte(
            cpf_masked="***.***.***-88",
            nome="Cônjuge",
            ano_base=2024,
            exercicio=2025,
            modelo=ModeloDeclaracao.completo,
            natureza=NaturezaContribuinte.dependente_titular,
        )
        d2.dependentes.append(_dep(RelacaoDependente.pai_mae, "Mãe"))
        a = IRPFAnalyzer([d1, d2])
        out = a.dependentes_count(2024)
        assert out["count"] == 2
        assert out["por_relacao"] == {"filho_filha": 1, "pai_mae": 1}


# =============================================================================
# dedutiveis_aplicados
# =============================================================================


class TestDedutiveisAplicados:
    def test_sem_pagamentos_retorna_dict_vazio_sparse(self):
        a = IRPFAnalyzer([_decl_empty()])
        out = a.dedutiveis_aplicados(2024)
        assert out == {}

    def test_apenas_saude_publicada_outras_omitidas(self):
        decl = _decl_empty()
        decl.pagamentos_efetuados.append(_pagamento(CodigoPagamentoDedutivel.saude, "18420.00"))
        a = IRPFAnalyzer([decl])
        out = a.dedutiveis_aplicados(2024)
        assert set(out.keys()) == {"saude"}
        assert out["saude"] == {
            "utilizado_brl": "18420.00",
            "teto_brl": None,
            "teto_aplicado": False,
        }

    def test_educacao_sem_dependentes_teto_unitario(self):
        decl = _decl_empty()
        decl.pagamentos_efetuados.append(_pagamento(CodigoPagamentoDedutivel.educacao, "2100.00"))
        a = IRPFAnalyzer([decl])
        out = a.dedutiveis_aplicados(2024)
        # Sem dependentes: titular conta como 1 pessoa.
        assert out["educacao"]["utilizado_brl"] == "2100.00"
        assert out["educacao"]["teto_brl"] == str(EDUCACAO_TETO_PER_PESSOA)
        assert out["educacao"]["teto_aplicado"] is False  # subutilizado

    def test_educacao_com_2_dependentes_teto_agregado(self):
        decl = _decl_empty()
        decl.dependentes.extend(
            [
                _dep(RelacaoDependente.filho_filha, "Filho 1"),
                _dep(RelacaoDependente.filho_filha, "Filho 2"),
            ]
        )
        decl.pagamentos_efetuados.append(_pagamento(CodigoPagamentoDedutivel.educacao, "5000.00"))
        a = IRPFAnalyzer([decl])
        out = a.dedutiveis_aplicados(2024)
        # (2 dependentes + titular) × 3561.50 = 10684.50
        assert out["educacao"]["teto_brl"] == str(EDUCACAO_TETO_PER_PESSOA * 3)
        assert out["educacao"]["utilizado_brl"] == "5000.00"
        assert out["educacao"]["teto_aplicado"] is False

    def test_educacao_no_teto_marca_teto_aplicado(self):
        decl = _decl_empty()
        decl.pagamentos_efetuados.append(
            _pagamento(
                CodigoPagamentoDedutivel.educacao,
                str(EDUCACAO_TETO_PER_PESSOA),
            )
        )
        a = IRPFAnalyzer([decl])
        out = a.dedutiveis_aplicados(2024)
        assert out["educacao"]["teto_aplicado"] is True

    def test_pensao_consolida_3_variantes_em_uma_chave(self):
        decl = _decl_with_3_variantes_pensao()
        out = IRPFAnalyzer([decl]).dedutiveis_aplicados(2024)
        # Apenas uma chave consolidada (D4)
        assert "pensao_alimenticia" in out
        assert "pensao_alimenticia_judicial" not in out
        assert out["pensao_alimenticia"]["utilizado_brl"] == "17500.00"
        assert out["pensao_alimenticia"]["teto_brl"] is None

    def test_pgbl_excluido_do_payload_aplicados(self):
        decl = _decl_empty()
        decl.pagamentos_efetuados.append(_pagamento(CodigoPagamentoDedutivel.pgbl, "12000.00"))
        a = IRPFAnalyzer([decl])
        out = a.dedutiveis_aplicados(2024)
        # PGBL tem card próprio (ADR-189); não duplicar.
        assert "pgbl" not in out

    def test_categorias_nao_acionaveis_excluidas(self):
        """outro/livro_caixa/funpresp/inss_empregado/filantropica não publicam."""
        decl = _decl_empty()
        decl.pagamentos_efetuados.extend(
            [
                _pagamento(CodigoPagamentoDedutivel.livro_caixa, "1000.00"),
                _pagamento(CodigoPagamentoDedutivel.contribuicao_funpresp, "500.00"),
                _pagamento(CodigoPagamentoDedutivel.contribuicao_inss_empregado, "300.00"),
                _pagamento(
                    CodigoPagamentoDedutivel.contribuicao_entidade_filantropica,
                    "200.00",
                ),
                _pagamento(CodigoPagamentoDedutivel.outro, "100.00"),
            ]
        )
        a = IRPFAnalyzer([decl])
        out = a.dedutiveis_aplicados(2024)
        assert out == {}  # nada publicado

    def test_mix_completo_sparse(self):
        """Saúde + Educação (com dependente, subutilizada) + INSS — pensão omitida."""
        decl = _decl_empty()
        decl.dependentes.append(_dep(RelacaoDependente.filho_filha, "Filho"))
        decl.pagamentos_efetuados.extend(
            [
                _pagamento(CodigoPagamentoDedutivel.saude, "18420.00"),
                _pagamento(CodigoPagamentoDedutivel.educacao, "2100.00"),
                _pagamento(CodigoPagamentoDedutivel.previdencia_oficial, "8176.00"),
            ]
        )
        a = IRPFAnalyzer([decl])
        out = a.dedutiveis_aplicados(2024)
        assert set(out.keys()) == {"saude", "educacao", "previdencia_oficial"}
        # Educação: 2 pessoas × 3561.50 = 7123.00
        assert out["educacao"]["teto_brl"] == str(EDUCACAO_TETO_PER_PESSOA * 2)
        assert out["saude"]["teto_brl"] is None
        assert out["previdencia_oficial"]["teto_brl"] is None

    def test_teto_aplicado_propaga_do_llm(self):
        """Se LLM truncou item (`teto_aplicado=True`), aggregate sinaliza."""
        decl = _decl_empty()
        decl.pagamentos_efetuados.append(
            _pagamento(CodigoPagamentoDedutivel.educacao, "3561.50", teto_aplicado=True)
        )
        a = IRPFAnalyzer([decl])
        out = a.dedutiveis_aplicados(2024)
        assert out["educacao"]["teto_aplicado"] is True

    def test_rounding_decimal_quantize(self):
        """Soma de Decimal não introduz float drift."""
        decl = _decl_empty()
        decl.pagamentos_efetuados.extend(
            [
                _pagamento(CodigoPagamentoDedutivel.saude, "100.10"),
                _pagamento(CodigoPagamentoDedutivel.saude, "200.20"),
                _pagamento(CodigoPagamentoDedutivel.saude, "300.30"),
            ]
        )
        a = IRPFAnalyzer([decl])
        out = a.dedutiveis_aplicados(2024)
        assert out["saude"]["utilizado_brl"] == "600.60"
        # Garante Decimal-as-string sem notação científica
        assert "e" not in out["saude"]["utilizado_brl"].lower()
        # Round-trip Decimal preservado
        assert Decimal(out["saude"]["utilizado_brl"]) == Decimal("600.60")
