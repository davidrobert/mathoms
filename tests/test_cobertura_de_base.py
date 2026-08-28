"""Cobertura de base no payload — toda razão publicada reproduz sobre a base que declara.

Gate de **Completude** da [[A40.l80]] ([[ADR-412]] §Consequências): *"não enumere
leitores — enumere números publicados"*, e *"toda razão publicada reproduz ao
recomputar numerador ÷ base declarada, em cents"*.

Checagem de PRESENÇA não serve: as três declarações falsas medidas nesta lane
(`protecao_cobertura`, `_reserva` do catálogo de KPI, e `reserva_emergencia.base_do_piso`)
tinham o campo preenchido e mentiam. Só o recompute discrimina.

**Eixo que este gate NÃO fecha**, e que precisa de dono próprio: razão publicada por
superfície TypeScript (`HeroKpiGrid.tsx` fabrica `financeiro / liquido` sobre uma base
que nenhum produtor declara) e o DTO read-time de `exposicao_cambial_v2.py`, cujo
`extra="forbid"` impede publicar o nome da base sem migrar o contrato.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.bases_financeiras import BaseFinanceira, publicar_bases
from pipeline.domain.services.ratios_calculator import RatiosCalculator

# As seis bases saem DUAS-A-DUAS DISTINTAS de propósito. O golden do dogfood tem
# `investimentos_nao_atribuidos = 0` e `cat2_efetivo = 0`, o que faz QUATRO das seis
# valerem o mesmo número — um gate de recompute rodado ali passa com qualquer base
# substituída, inclusive a amputada, e nasce imune a mutação.
_CRUS = {
    "investimentos_titular": 400_000.0,
    "investimentos_conjuge": 150_000.0,
    "investimentos_nao_atribuidos": 300_000.0,
    "caixa_total_brl": 50_000.0,
    # Geradores ⊆ cat_2 completo: é essa diferença que separa `carteira_produtiva_fixa`
    # (concentração, toggle-independente) da `carteira_produtiva_familia` (bloco IF).
    "cat2_efetivo": 200_000.0,
    "imoveis_investimento": 900_000.0,
    "bruto": 2_400_000.0,
    # 500k, não 600k: com 600k o `patrimonio_liquido` empatava com a
    # `carteira_produtiva_fixa` e o teste de discriminação reprovava — corretamente.
    "dividas": 500_000.0,
}


_FLUXO = {
    "janela_12m": {
        "receita_recorrente": 120_000,
        "receita_total": 130_000,
        "despesa_total": 60_000,
        "despesa_mensal_media": 5_000,
        "despesa_mensal_essencial": 0.0,
        "periodo": "2025-04 a 2026-03",
        "n_meses": 12,
    }
}


@pytest.fixture
def patrimonio() -> dict:
    valores = dict(_CRUS)
    publicado = publicar_bases(valores)
    investivel = publicado["bases"][BaseFinanceira.carteira_financeira_familia.value]["valor_brl"]
    return {**valores, "investivel_financeiro": investivel, **publicado}


# O gate lê a declaração DO PRODUTOR, nunca um membro do enum escrito à mão aqui:
# fixar o membro no teste o deixa cego justamente quando o produtor declara a base
# errada, que é a classe de defeito que este arquivo existe para pegar. Medido — a
# primeira versão deste gate passava com a homônima substituída no produtor.
@pytest.fixture
def ratios(patrimonio: dict) -> dict:
    return RatiosCalculator().calculate(_FLUXO, patrimonio).to_legacy_dict()


def _cents(valor: float) -> int:
    return int((Decimal(str(valor)) * 100).quantize(Decimal("1")))


def test_a_fixture_discrimina_as_bases(patrimonio: dict) -> None:
    """Sem isto o gate abaixo é vacuoso: mutação da base não o deixaria vermelho."""
    valores = [b["valor_brl"] for b in patrimonio["bases"].values()]

    assert len(set(valores)) == len(valores), f"bases não distintas: {valores}"


def test_concentracao_reproduz_sobre_a_base_que_declara(patrimonio: dict, ratios: dict) -> None:
    """O recompute é o gate; presença do campo passaria com o rótulo errado."""
    declarada = ratios["base_concentracao_imobiliaria"]
    assert declarada in {b.value for b in BaseFinanceira}, f"base fora do enum: {declarada}"

    base = patrimonio["bases"][declarada]["valor_brl"]
    numerador = patrimonio["imoveis_investimento"]

    esperado = _cents(round(numerador / base * 100.0, 2))
    publicado = _cents(ratios["concentracao_imobiliaria"])

    assert publicado == esperado, f"concentração não reproduz sobre `{declarada}`"


# É o que separa este gate de um que só confere presença — e o que impede que a
# homônima `carteira_produtiva_familia`, 5,6× menor no dogfood, passe por certa.
def test_nenhuma_OUTRA_base_reproduz_a_concentracao(patrimonio: dict, ratios: dict) -> None:
    """Mata o falso-verde: a base declarada tem de ser a ÚNICA que reproduz."""
    publicado = _cents(ratios["concentracao_imobiliaria"])
    numerador = patrimonio["imoveis_investimento"]

    reproduzem = [
        nome
        for nome, base in patrimonio["bases"].items()
        if base["valor_brl"] > 0
        and _cents(round(numerador / base["valor_brl"] * 100.0, 2)) == publicado
    ]

    assert reproduzem == [
        BaseFinanceira.carteira_produtiva_fixa.value
    ], f"mais de uma base reproduz o número — o gate não discrimina: {reproduzem}"


def test_a_base_da_concentracao_nao_e_a_homonima(patrimonio: dict, ratios: dict) -> None:
    """`carteira_produtiva_familia` conta só geradores e zera com o toggle off."""
    declarada = ratios["base_concentracao_imobiliaria"]
    familia = BaseFinanceira.carteira_produtiva_familia.value

    assert declarada != familia, "a razão declara a homônima — 5,6× menor no dogfood"
    assert patrimonio["bases"][declarada]["valor_brl"] != patrimonio["bases"][familia]["valor_brl"]
