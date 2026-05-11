"""Unit tests for ADR-189 — IRPFAnalyzer.pgbl_status + pgbl_resumo (4 estados + edges)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer, PgblStatus
from pipeline.llm.schemas.e16_irpf_full import (
    CodigoPagamentoDedutivel,
    CodigoRendimentoIsento,
    Contribuinte,
    FontePagadoraPJ,
    ImpostoApurado,
    IRPFFullOutput,
    ModeloDeclaracao,
    NaturezaContribuinte,
    PagamentoDedutivel,
    RendimentoIsento,
)


def _contrib(
    modelo: ModeloDeclaracao,
    ano: int = 2024,
    natureza: NaturezaContribuinte = NaturezaContribuinte.titular,
) -> Contribuinte:
    return Contribuinte(
        cpf_masked="***.***.***-99",
        nome="Test User",
        ano_base=ano,
        exercicio=ano + 1,
        modelo=modelo,
        natureza=natureza,
    )


_ZERO_IMPOSTO = dict(
    base_calculo_brl="0",
    ir_devido_brl="0",
    deducoes_totais_brl="0",
    ir_pago_brl="0",
    ir_a_pagar_brl="0",
)


def _fonte_pj(rendimento: str) -> FontePagadoraPJ:
    return FontePagadoraPJ(
        cnpj="**.***.***/****-**",
        nome="ACME",
        rendimentos_tributaveis_brl=rendimento,
        contrib_previdenciaria_brl="0",
        ir_retido_brl="0",
    )


def _pgbl_pagamento(valor: str) -> PagamentoDedutivel:
    return PagamentoDedutivel(
        codigo_rfb=CodigoPagamentoDedutivel.pgbl,
        beneficiario_nome="Itau Prev",
        valor_pago_brl=valor,
        valor_dedutivel_brl=valor,
    )


def _decl(
    *,
    modelo: ModeloDeclaracao = ModeloDeclaracao.completo,
    ano: int = 2024,
    rendimento_pj: str = "150000.00",
    pgbl_aportado: str | None = None,
    natureza: NaturezaContribuinte = NaturezaContribuinte.titular,
) -> IRPFFullOutput:
    out = IRPFFullOutput(
        contribuinte=_contrib(modelo, ano, natureza),
        rendimentos_pj=[_fonte_pj(rendimento_pj)],
        imposto_apurado=ImpostoApurado(**_ZERO_IMPOSTO),
        confidence=0.95,
    )
    if pgbl_aportado is not None:
        out.pagamentos_efetuados.append(_pgbl_pagamento(pgbl_aportado))
    return out


class TestPgblStatusCapacidadeDisponivel:
    def test_completa_sem_aporte_retorna_capacidade_disponivel(self):
        a = IRPFAnalyzer([_decl(rendimento_pj="200000.00")])
        assert a.pgbl_status(2024) == PgblStatus.capacidade_disponivel
        # 12% × 200k = 24k de capacidade
        assert a.pgbl_capacidade_dedutivel(2024) == Decimal("24000.00")

    def test_completa_com_aporte_parcial_retorna_capacidade_disponivel(self):
        a = IRPFAnalyzer([_decl(rendimento_pj="200000.00", pgbl_aportado="10000.00")])
        assert a.pgbl_status(2024) == PgblStatus.capacidade_disponivel
        # 12% × 200k - 10k = 14k
        assert a.pgbl_capacidade_dedutivel(2024) == Decimal("14000.00")


class TestPgblStatusModeloSimplificado:
    def test_solo_simplificado_retorna_modelo_simplificado(self):
        a = IRPFAnalyzer([_decl(modelo=ModeloDeclaracao.simplificado, rendimento_pj="200000.00")])
        assert a.pgbl_status(2024) == PgblStatus.modelo_simplificado

    def test_casal_ambos_simplificado_retorna_modelo_simplificado(self):
        d1 = _decl(modelo=ModeloDeclaracao.simplificado, rendimento_pj="100000.00")
        d2 = _decl(
            modelo=ModeloDeclaracao.simplificado,
            rendimento_pj="80000.00",
            natureza=NaturezaContribuinte.dependente_titular,
        )
        a = IRPFAnalyzer([d1, d2])
        assert a.pgbl_status(2024) == PgblStatus.modelo_simplificado

    def test_casal_misto_simpl_mais_completa_nao_e_modelo_simplificado(self):
        # Se ao menos 1 declaração é completa, o ano não fica bloqueado pelo regime —
        # cai em capacidade_disponivel ou no_teto.
        d_simpl = _decl(modelo=ModeloDeclaracao.simplificado, rendimento_pj="80000.00")
        d_compl = _decl(
            modelo=ModeloDeclaracao.completo,
            rendimento_pj="150000.00",
            natureza=NaturezaContribuinte.dependente_titular,
        )
        a = IRPFAnalyzer([d_simpl, d_compl])
        assert a.pgbl_status(2024) != PgblStatus.modelo_simplificado
        # Capacidade vem só da completa: 12% × 150k = 18k
        assert a.pgbl_status(2024) == PgblStatus.capacidade_disponivel


class TestPgblStatusNoTeto:
    def test_completa_aporte_exato_no_teto(self):
        # 12% × 200k = 24k aportado → capacidade = 0
        a = IRPFAnalyzer([_decl(rendimento_pj="200000.00", pgbl_aportado="24000.00")])
        assert a.pgbl_status(2024) == PgblStatus.no_teto
        assert a.pgbl_capacidade_dedutivel(2024) == Decimal("0")

    def test_completa_aporte_acima_do_teto_max_zero(self):
        """Edge: aporte acima de 12% trunca via max(0, ...) — vira no_teto."""
        a = IRPFAnalyzer([_decl(rendimento_pj="100000.00", pgbl_aportado="30000.00")])
        # 12% × 100k = 12k; aportado 30k > teto → capacidade truncada a 0
        assert a.pgbl_capacidade_dedutivel(2024) == Decimal("0")
        assert a.pgbl_status(2024) == PgblStatus.no_teto


class TestPgblStatusSemRendaTributavel:
    def test_sem_declaracao_retorna_sem_renda_tributavel(self):
        a = IRPFAnalyzer([])
        assert a.pgbl_status(2024) == PgblStatus.sem_renda_tributavel

    def test_completa_so_isentos_retorna_sem_renda_tributavel(self):
        decl = IRPFFullOutput(
            contribuinte=_contrib(ModeloDeclaracao.completo),
            imposto_apurado=ImpostoApurado(**_ZERO_IMPOSTO),
            confidence=0.95,
        )
        decl.rendimentos_isentos.append(
            RendimentoIsento(
                codigo_rfb=CodigoRendimentoIsento.lucros_dividendos,
                descricao="Lucros",
                valor_brl="100000.00",
            )
        )
        a = IRPFAnalyzer([decl])
        assert a.rendimentos_tributaveis(2024) == Decimal("0")
        assert a.pgbl_status(2024) == PgblStatus.sem_renda_tributavel


class TestPgblResumo:
    def test_completa_sem_aporte_resumo(self):
        a = IRPFAnalyzer([_decl(rendimento_pj="200000.00")])
        r = a.pgbl_resumo(2024)
        assert r.aportado_brl == Decimal("0")
        assert r.teto_brl == Decimal("24000.00")

    def test_completa_com_aporte_resumo(self):
        a = IRPFAnalyzer([_decl(rendimento_pj="200000.00", pgbl_aportado="10000.00")])
        r = a.pgbl_resumo(2024)
        assert r.aportado_brl == Decimal("10000.00")
        assert r.teto_brl == Decimal("24000.00")

    def test_simplificado_teto_zero(self):
        """No simplificado, teto dedutível = 0 (regime não permite dedução)."""
        a = IRPFAnalyzer(
            [
                _decl(
                    modelo=ModeloDeclaracao.simplificado,
                    rendimento_pj="200000.00",
                    pgbl_aportado="5000.00",
                )
            ]
        )
        r = a.pgbl_resumo(2024)
        assert r.teto_brl == Decimal("0")
        # Aportado é registrado mesmo no simplificado (informativo)
        assert r.aportado_brl == Decimal("5000.00")

    def test_ano_sem_declaracoes_resumo_zero(self):
        a = IRPFAnalyzer([])
        r = a.pgbl_resumo(2024)
        assert r.aportado_brl == Decimal("0")
        assert r.teto_brl == Decimal("0")
