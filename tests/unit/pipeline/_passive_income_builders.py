"""Fixture builders compartilhados pelos testes do PassiveIncomeCalculator."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.passive_income_calculator import (  # noqa: E402
    PassiveIncomeCalculator,
    PassiveIncomeConfig,
)
from pipeline.llm.schemas.e16_irpf_full import (  # noqa: E402
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
    Contribuinte,
    ImpostoApurado,
    IRPFFullOutput,
    ModeloDeclaracao,
    NaturezaContribuinte,
    PatrimonialItem,
    RendimentoExterior,
    RendimentoIsento,
    RendimentoTribExclusiva,
)


def contribuinte(ano_base: int = 2024, nome: str = "Test") -> Contribuinte:
    return Contribuinte(
        cpf_masked="***.***.***-99",
        nome=nome,
        ano_base=ano_base,
        exercicio=ano_base + 1,
        modelo=ModeloDeclaracao.completo,
        natureza=NaturezaContribuinte.titular,
    )


def imposto(ir_pago: str = "0") -> ImpostoApurado:
    return ImpostoApurado(
        base_calculo_brl="0",
        ir_devido_brl="0",
        deducoes_totais_brl="0",
        ir_pago_brl=ir_pago,
    )


def isento(
    codigo: CodigoRendimentoIsento,
    valor: str,
    *,
    descricao: str | None = None,
    fonte: str | None = None,
) -> RendimentoIsento:
    return RendimentoIsento(
        codigo_rfb=codigo,
        descricao=descricao or f"isento {codigo.value}",
        valor_brl=valor,
        fonte=fonte,
    )


def bem(
    *,
    codigo: str = "32",
    descricao: str,
    ano: int = 2024,
    valor: str = "100000.00",
    categoria: str = "investimento",
) -> PatrimonialItem:
    return PatrimonialItem(
        codigo=codigo,
        descricao=descricao,
        categoria=categoria,
        valor_brl=valor,
        membro_key="titular",
        ano=ano,
    )


def exclusiva(codigo: CodigoRendimentoTribExclusiva, valor: str) -> RendimentoTribExclusiva:
    return RendimentoTribExclusiva(
        codigo_rfb=codigo,
        descricao=f"exclusiva {codigo.value}",
        valor_brl=valor,
    )


def exterior_rend(valor: str) -> RendimentoExterior:
    return RendimentoExterior(
        pais="USA",
        pagador="Vanguard",
        valor_origem="100.00",
        moeda_origem="USD",
        taxa_conversao="5.00",
        data_conversao=date(2024, 6, 1),
        valor_brl=valor,
    )


def decl(
    *,
    ano_base: int = 2024,
    isentos: list | None = None,
    exclusiva_list: list | None = None,
    exterior: list | None = None,
    bens: list | None = None,
) -> IRPFFullOutput:
    return IRPFFullOutput(
        contribuinte=contribuinte(ano_base=ano_base),
        rendimentos_isentos=isentos or [],
        rendimentos_tributacao_exclusiva=exclusiva_list or [],
        rendimentos_exterior=exterior or [],
        bens_direitos=bens or [],
        imposto_apurado=imposto(),
        confidence=0.95,
    )


def patrimonio(
    *,
    investimentos_titular: float = 1_000_000.0,
    investimentos_conjuge: float = 0.0,
    imoveis_investimento: float = 0.0,
    residencia: float = 0.0,
    veiculos: float = 0.0,
    caixa: float = 0.0,
    derivativos: float = 0.0,
) -> dict:
    return {
        "investimentos_titular": investimentos_titular,
        "investimentos_conjuge": investimentos_conjuge,
        "imoveis_investimento": imoveis_investimento,
        "residencia": residencia,
        "veiculos": veiculos,
        "caixa_total_brl": caixa,  # CTO-02: chave canônica (era caixa_moeda_estrangeira)
        "derivativos": derivativos,
    }


def holdings(positions: list[dict]) -> dict:
    return {"dados": positions, "total_por_membro": {}, "total_geral": 0.0}


def calc(config: PassiveIncomeConfig | None = None) -> PassiveIncomeCalculator:
    return PassiveIncomeCalculator(config or PassiveIncomeConfig())
