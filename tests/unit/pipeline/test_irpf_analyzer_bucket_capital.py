"""IRPFAnalyzer bucket capital — re-classificação aluguel PF (A8.3 PR-B)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer
from pipeline.llm.schemas.e16_irpf_full import (
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
    Contribuinte,
    FontePagadoraPF,
    FontePagadoraPJ,
    ImpostoApurado,
    IRPFFullOutput,
    ModeloDeclaracao,
    NaturezaContribuinte,
    RendimentoIsento,
    RendimentoTribExclusiva,
)


def _contribuinte(ano_base: int = 2024) -> Contribuinte:
    return Contribuinte(
        cpf_masked="***.***.***-99",
        nome="Test User",
        ano_base=ano_base,
        exercicio=ano_base + 1,
        modelo=ModeloDeclaracao.completo,
        natureza=NaturezaContribuinte.titular,
    )


def _imposto(ir_pago: str = "10000.00") -> ImpostoApurado:
    return ImpostoApurado(
        base_calculo_brl="100000.00",
        ir_devido_brl="15000.00",
        deducoes_totais_brl="5000.00",
        ir_pago_brl=ir_pago,
    )


def _pj(rendimentos: str, ir_retido: str = "0.00") -> FontePagadoraPJ:
    return FontePagadoraPJ(
        cnpj="12.345.678/0001-90",
        nome="ACME LTDA",
        rendimentos_tributaveis_brl=rendimentos,
        contrib_previdenciaria_brl="0.00",
        ir_retido_brl=ir_retido,
    )


def _pf(valor: str, pagador: str = "Inquilino Ficcional") -> FontePagadoraPF:
    return FontePagadoraPF(
        pagador_cpf_masked="***.***.***-77",
        pagador_nome=pagador,
        valor_brl=valor,
        ir_recolhido_brl="0.00",
    )


def _decl(
    *,
    rendimentos_pj: list[FontePagadoraPJ] | None = None,
    rendimentos_pf: list[FontePagadoraPF] | None = None,
    rendimentos_isentos: list[RendimentoIsento] | None = None,
    rendimentos_exclusiva: list[RendimentoTribExclusiva] | None = None,
) -> IRPFFullOutput:
    return IRPFFullOutput(
        contribuinte=_contribuinte(),
        rendimentos_pj=rendimentos_pj or [],
        rendimentos_pf=rendimentos_pf or [],
        rendimentos_isentos=rendimentos_isentos or [],
        rendimentos_tributacao_exclusiva=rendimentos_exclusiva or [],
        imposto_apurado=_imposto(),
        confidence=0.95,
    )


def _isento(codigo: CodigoRendimentoIsento, descricao: str, valor: str) -> RendimentoIsento:
    return RendimentoIsento(codigo_rfb=codigo, descricao=descricao, valor_brl=valor)


def _excl(
    codigo: CodigoRendimentoTribExclusiva, descricao: str, valor: str
) -> RendimentoTribExclusiva:
    return RendimentoTribExclusiva(codigo_rfb=codigo, descricao=descricao, valor_brl=valor)


class TestBucketCapitalAluguel:
    def test_aluguel_pf_vai_para_capital(self):
        """Aluguel PF (carnê-leão) entra em capital, não trabalho."""
        decl = _decl(
            rendimentos_pj=[_pj("100000.00")],
            rendimentos_pf=[_pf("36000.00")],
        )
        sp = IRPFAnalyzer([decl]).split_trabalho_vs_capital(2024)
        assert sp.trabalho_brl == Decimal("100000.00")
        assert sp.capital_brl == Decimal("36000.00")

    def test_sem_aluguel_idempotente_com_pj_e_dividendos(self):
        """Sem rendimentos_pf, split mantém comportamento legado."""
        decl = _decl(
            rendimentos_pj=[_pj("200000.00")],
            rendimentos_isentos=[
                _isento(CodigoRendimentoIsento.lucros_dividendos, "Div", "20000.00")
            ],
            rendimentos_exclusiva=[
                _excl(CodigoRendimentoTribExclusiva.decimo_terceiro, "13o", "15000.00")
            ],
        )
        sp = IRPFAnalyzer([decl]).split_trabalho_vs_capital(2024)
        # Idempotência: PJ 200k + 13º 15k = 215k trabalho; lucros 20k capital.
        assert sp.trabalho_brl == Decimal("215000.00")
        assert sp.capital_brl == Decimal("20000.00")

    def test_aluguel_e_servico_no_mesmo_declarante(self):
        """Múltiplos pagadores PF — todos somam em capital (schema = aluguel)."""
        decl = _decl(
            rendimentos_pj=[_pj("80000.00")],
            rendimentos_pf=[
                _pf("18000.00", pagador="Inquilino A"),
                _pf("12000.00", pagador="Inquilino B"),
            ],
        )
        sp = IRPFAnalyzer([decl]).split_trabalho_vs_capital(2024)
        assert sp.trabalho_brl == Decimal("80000.00")
        assert sp.capital_brl == Decimal("30000.00")

    def test_pj_nunca_migra_para_capital(self):
        """rendimentos_pj é trabalho por design (CLT/PJ work) — nunca capital."""
        decl = _decl(
            rendimentos_pj=[_pj("150000.00"), _pj("50000.00")],
        )
        sp = IRPFAnalyzer([decl]).split_trabalho_vs_capital(2024)
        assert sp.trabalho_brl == Decimal("200000.00")
        assert sp.capital_brl == Decimal("0")

    def test_aluguel_combina_com_dividendos_e_jcp_em_capital(self):
        """Capital agrega aluguel PF + dividendos isentos + JCP exclusiva."""
        decl = _decl(
            rendimentos_pj=[_pj("100000.00")],
            rendimentos_pf=[_pf("24000.00")],
            rendimentos_isentos=[
                _isento(CodigoRendimentoIsento.lucros_dividendos, "Lucros", "10000.00")
            ],
            rendimentos_exclusiva=[_excl(CodigoRendimentoTribExclusiva.jcp, "JCP", "3500.00")],
        )
        sp = IRPFAnalyzer([decl]).split_trabalho_vs_capital(2024)
        assert sp.trabalho_brl == Decimal("100000.00")
        # 24k aluguel + 10k lucros + 3.5k JCP = 37.5k
        assert sp.capital_brl == Decimal("37500.00")

    def test_total_brl_preservado_apos_realocacao(self):
        """Re-classificação não muda total — só desloca entre buckets."""
        decl = _decl(
            rendimentos_pj=[_pj("90000.00")],
            rendimentos_pf=[_pf("20000.00")],
            rendimentos_exclusiva=[
                _excl(CodigoRendimentoTribExclusiva.decimo_terceiro, "13o", "7500.00")
            ],
        )
        sp = IRPFAnalyzer([decl]).split_trabalho_vs_capital(2024)
        # Total invariante: 90k + 20k + 7.5k = 117.5k.
        assert sp.total_brl == Decimal("117500.00")
        assert sp.trabalho_brl == Decimal("97500.00")
        assert sp.capital_brl == Decimal("20000.00")

    def test_rendimento_pf_zero_e_idempotente(self):
        """Edge case: rendimentos_pf vazio = comportamento prévio exato."""
        decl = _decl(rendimentos_pj=[_pj("60000.00")])
        sp = IRPFAnalyzer([decl]).split_trabalho_vs_capital(2024)
        assert sp.trabalho_brl == Decimal("60000.00")
        assert sp.capital_brl == Decimal("0")
