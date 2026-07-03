"""Invariantes da lane A28.l3 — ano-base fiscal único PGBL (ADR-305).

Cobertura: resolver ``ano_base_fiscal`` (nota de degradação), fonte única entre
``irpf_kpis`` e ``previdencia_pgbl`` (statement count == 1), coerência entre
``pgbl_status`` e aporte recomendado, e propagação da nota de degradação nos
dois payloads. Fixtures sintéticas PII-zero (CPFs mascarados, valores fictícios).
"""

from __future__ import annotations

import datetime as _dt
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.e5_analyzer_adapter import _build_capacidade_pgbl
from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer, PgblStatus
from pipeline.domain.services.irpf_completude import CompletudeAno, resolve_ano_base_fiscal
from pipeline.domain.services.previdencia_analyzer import PrevidenciaAnalyzer
from pipeline.llm.schemas.e16_irpf_full import (
    CodigoPagamentoDedutivel,
    Contribuinte,
    FontePagadoraPJ,
    ImpostoApurado,
    IRPFFullOutput,
    ModeloDeclaracao,
    NaturezaContribuinte,
    PagamentoDedutivel,
)
from scripts.e5_analyze import _e5_kpis_from_analyzer

_HOJE_POS_PRAZO = _dt.date(2026, 7, 1)  # 2025 fora da janela RFB (fechado em 1/jun)

_CPF_TITULAR = "***.***.***-36"
_CPF_CONJUGE = "***.***.***-60"


def _zero_imposto() -> ImpostoApurado:
    return ImpostoApurado(
        base_calculo_brl=Decimal("0"),
        ir_devido_brl=Decimal("0"),
        deducoes_totais_brl=Decimal("0"),
        ir_pago_brl=Decimal("0"),
        ir_a_pagar_brl=Decimal("0"),
    )


def _pgbl_pagamento(valor: str) -> PagamentoDedutivel:
    return PagamentoDedutivel(
        codigo_rfb=CodigoPagamentoDedutivel.pgbl,
        beneficiario_nome="Seguradora Ficticia",
        valor_pago_brl=Decimal(valor),
        valor_dedutivel_brl=Decimal(valor),
    )


def _fontes_pj(renda_pj: str) -> list[FontePagadoraPJ]:
    if Decimal(renda_pj) <= 0:
        return []
    return [
        FontePagadoraPJ(
            cnpj="**.***.***/****-**",
            nome="Fonte Ficticia",
            rendimentos_tributaveis_brl=Decimal(renda_pj),
            contrib_previdenciaria_brl=Decimal("0"),
            ir_retido_brl=Decimal("0"),
        )
    ]


def _contrib(cpf: str, ano: int) -> Contribuinte:
    return Contribuinte(
        cpf_masked=cpf,
        nome="TITULAR" if cpf == _CPF_TITULAR else "CONJUGE",
        ano_base=ano,
        exercicio=ano + 1,
        modelo=ModeloDeclaracao.completo,
        natureza=NaturezaContribuinte.titular,
    )


def _decl(
    *,
    cpf: str,
    ano: int,
    renda_pj: str = "0",
    pgbl_aportado: str | None = None,
) -> IRPFFullOutput:
    pagamentos = [_pgbl_pagamento(pgbl_aportado)] if pgbl_aportado else []
    return IRPFFullOutput(
        contribuinte=_contrib(cpf, ano),
        rendimentos_pj=_fontes_pj(renda_pj),
        pagamentos_efetuados=pagamentos,
        imposto_apurado=_zero_imposto(),
        confidence=0.95,
    )


def _analyzer_dogfood_shape() -> IRPFAnalyzer:
    """Reproduz a forma do dogfood 72883bde: 2024 completo (casal, teto PGBL
    atingido), 2025 incompleto (falta o cônjuge) com renda tributável sobrando."""
    decls = [
        _decl(cpf=_CPF_TITULAR, ano=2024, renda_pj="100000", pgbl_aportado="12000"),
        _decl(cpf=_CPF_CONJUGE, ano=2024, renda_pj="50000", pgbl_aportado="6000"),
        _decl(cpf=_CPF_TITULAR, ano=2025, renda_pj="120000"),
    ]
    return IRPFAnalyzer(decls)


# -----------------------------------------------------------------------------
# Resolver ano_base_fiscal (ADR-305 D1/D3)
# -----------------------------------------------------------------------------


def _resolve(analyzer: IRPFAnalyzer):
    return resolve_ano_base_fiscal(analyzer.estados_completude(_HOJE_POS_PRAZO))


def test_resolver_escolhe_ultimo_completo_e_nota_degradacao():
    resolved = _resolve(_analyzer_dogfood_shape())
    assert resolved is not None
    assert resolved.ano == 2024
    assert resolved.completude == CompletudeAno.completo
    assert resolved.nota_degradacao is not None
    assert "2024" in resolved.nota_degradacao
    assert "2025 incompleto" in resolved.nota_degradacao
    assert _CPF_CONJUGE in resolved.nota_degradacao  # motivo do ano recente


def test_resolver_sem_ano_mais_recente_nao_degrada():
    analyzer = IRPFAnalyzer([_decl(cpf=_CPF_TITULAR, ano=2024, renda_pj="100000")])
    resolved = _resolve(analyzer)
    assert resolved is not None
    assert resolved.ano == 2024
    assert resolved.nota_degradacao is None


def test_resolver_sem_declaracoes_retorna_none():
    assert _resolve(IRPFAnalyzer([])) is None


# -----------------------------------------------------------------------------
# Fonte única: irpf_kpis e previdencia_pgbl no MESMO ano-base (ADR-305 D2/D4)
# -----------------------------------------------------------------------------


def _payloads_do_relatorio(analyzer: IRPFAnalyzer) -> tuple[dict, dict]:
    resolved = _resolve(analyzer)
    irpf_kpis = _e5_kpis_from_analyzer(analyzer, resolved)
    capacidade = _build_capacidade_pgbl(analyzer)
    previdencia = PrevidenciaAnalyzer().analyze({}, capacidade_irpf=capacidade)
    return irpf_kpis, previdencia.to_legacy_dict()


def test_igualdade_de_fonte_ano_base():
    irpf_kpis, previdencia = _payloads_do_relatorio(_analyzer_dogfood_shape())
    assert previdencia["ano_base"] == irpf_kpis["ano_base_default"] == irpf_kpis["ano_base"]


def test_pgbl_statement_count_eh_um():
    """Regressão dogfood 72883bde: nunca 'capacidade = 0' e 'capacidade > 0'
    no mesmo relatório. Ambas as seções leem o MESMO ano (2024, teto atingido)."""
    irpf_kpis, previdencia = _payloads_do_relatorio(_analyzer_dogfood_shape())
    kpis_capacidade = Decimal(irpf_kpis["pgbl_capacidade_dedutivel_brl"])
    recomendacao = Decimal(str(previdencia["limite_pgbl_anual"]))
    contradicao = (kpis_capacidade > 0) != (recomendacao > 0)
    assert not contradicao, f"kpis={kpis_capacidade} vs recomendacao={recomendacao}"
    assert kpis_capacidade == 0
    assert irpf_kpis["pgbl_status"] == PgblStatus.no_teto.value


def test_coerencia_status_e_aporte_recomendado():
    """ADR-305 D4c: aporte sugerido > 0 ⇒ pgbl_status == capacidade_disponivel."""
    analyzer = IRPFAnalyzer(
        [
            _decl(cpf=_CPF_TITULAR, ano=2024, renda_pj="100000", pgbl_aportado="2000"),
            _decl(cpf=_CPF_CONJUGE, ano=2024, renda_pj="50000"),
            _decl(cpf=_CPF_TITULAR, ano=2025, renda_pj="120000"),
        ]
    )
    irpf_kpis, previdencia = _payloads_do_relatorio(analyzer)
    assert previdencia["aporte_mensal"] > 0
    assert irpf_kpis["pgbl_status"] == PgblStatus.capacidade_disponivel.value
    assert previdencia["ano_base"] == irpf_kpis["ano_base"] == 2024


# -----------------------------------------------------------------------------
# Degradação explícita nos dois payloads (ADR-305 D3)
# -----------------------------------------------------------------------------


def test_nota_degradacao_presente_nos_dois_payloads():
    irpf_kpis, previdencia = _payloads_do_relatorio(_analyzer_dogfood_shape())
    assert irpf_kpis["ano_base_nota_degradacao"] is not None
    assert previdencia["nota_degradacao"] == irpf_kpis["ano_base_nota_degradacao"]


def test_nota_proxy_retrospectivo_na_recomendacao():
    """Co-design financial-planner: a nota explica que o espaço dedutível é do
    ano-calendário corrente e o ano-base entra como proxy."""
    _, previdencia = _payloads_do_relatorio(_analyzer_dogfood_shape())
    assert "ano-calendário corrente" in previdencia["nota"]


def test_sem_degradacao_campos_nulos():
    analyzer = IRPFAnalyzer([_decl(cpf=_CPF_TITULAR, ano=2024, renda_pj="100000")])
    irpf_kpis, previdencia = _payloads_do_relatorio(analyzer)
    assert irpf_kpis["ano_base_nota_degradacao"] is None
    assert previdencia["nota_degradacao"] is None
