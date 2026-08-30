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


# ---------------------------------------------------------------------------
# Autonomia — a medida E o piso, cada um sobre a base que declara
# ---------------------------------------------------------------------------


# Sem sufixo `_brl` no parâmetro: este arquivo é domínio `float` (o `ratios` inteiro é),
# e nome monetário sobre float é o P5 do ratchet — mesmo precedente de `base_da_meta_if`,
# onde o identificador interno perde o sufixo e a CHAVE publicada o mantém.
def _meses(base: float, divisor: float) -> float:
    """`max(0, base)` porque `investivel_financeiro` carrega clamp que a base não tem."""
    return round(max(0.0, base) / divisor, 2)


# O divisor é PUBLICADO (`autonomia_denominador_mensal_brl`) em vez de remontado de
# `fluxo_caixa`: `_resolve_window` tem fallback — sem `janela_12m` o `n_meses` vira 0 e a
# despesa sai de outro nó —, então recompute cross-bloco erraria exatamente ali.
def test_autonomia_reproduz_sobre_a_base_que_declara(ratios: dict, patrimonio: dict) -> None:
    """A MEDIDA declara sua base; até o #1782 só o piso declarava a dele."""
    declarada = ratios["base_autonomia_financeira"]
    assert declarada in {b.value for b in BaseFinanceira}, f"base fora do enum: {declarada}"

    base = patrimonio["bases"][declarada]["valor_brl"]
    divisor = ratios["autonomia_denominador_mensal_brl"]

    assert _meses(base, divisor) == ratios["autonomia_financeira_meses"]


def test_piso_da_autonomia_reproduz_sobre_a_base_que_declara(
    ratios: dict, patrimonio: dict
) -> None:
    """`base_do_piso` existia desde o PR3b e nunca fora recomposto — só declarado."""
    base = patrimonio["bases"][ratios["base_do_piso"]]["valor_brl"]
    divisor = ratios["autonomia_denominador_mensal_brl"]

    assert _meses(base, divisor) == ratios["piso_autonomia_financeira_meses"]


# Sem isto o par (medida, piso) poderia declarar a mesma base e os dois testes acima
# passariam — o intervalo colapsaria num ponto sem ninguém notar.
def test_medida_e_piso_declaram_bases_DIFERENTES(ratios: dict) -> None:
    """O piso é o extremo amputado; medida e piso iguais é intervalo degenerado."""
    assert ratios["base_autonomia_financeira"] != ratios["base_do_piso"]
    assert ratios["autonomia_financeira_meses"] > ratios["piso_autonomia_financeira_meses"]


def test_nenhuma_OUTRA_base_reproduz_a_autonomia(ratios: dict, patrimonio: dict) -> None:
    """Mesma trava do gate da concentração: a declarada tem de ser a única."""
    divisor = ratios["autonomia_denominador_mensal_brl"]
    medida = ratios["autonomia_financeira_meses"]

    reproduzem = [
        nome
        for nome, base in patrimonio["bases"].items()
        if _meses(base["valor_brl"], divisor) == medida
    ]

    assert reproduzem == [
        ratios["base_autonomia_financeira"]
    ], f"mais de uma base reproduz a autonomia — o gate não discrimina: {reproduzem}"


# ---------------------------------------------------------------------------
# Coerência entre superfícies — o catálogo não pode declarar outra base que o produtor
# ---------------------------------------------------------------------------


# O gate deriva o par pela CONVENÇÃO do produtor (`$.<bloco>.<x>` ⇒ `<bloco>.base_<x>`),
# não por lista escrita à mão: assim toda razão que passar a declarar base entra sozinha,
# e o gate mede classe em vez de instância. Foi por não existir que `kpi_targets[].base`
# declarou `"carteira_produtiva"` (fora do enum, vizinho 5,6× menor) para o MESMO
# `observado_path` que o produtor declarava `carteira_produtiva_fixa`.
def _declaracao_do_produtor(e5: dict, observado_path: str) -> str | None:
    partes = observado_path.removeprefix("$.").split(".")
    if len(partes) != 2:
        return None
    bloco, folha = partes
    return (e5.get(bloco) or {}).get(f"base_{folha}")


def test_catalogo_declara_a_MESMA_base_que_o_produtor(patrimonio: dict, ratios: dict) -> None:
    """Duas declarações divergentes para o mesmo número é o C14 um nível acima."""
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets

    e5 = {"patrimonio": patrimonio, "ratios": ratios}
    alvos = build_kpi_targets(e5, scoring={})

    divergentes = {
        chave: (alvo["base"], do_produtor)
        for chave, alvo in alvos.items()
        if (do_produtor := _declaracao_do_produtor(e5, alvo["observado_path"]))
        and alvo["base"] != do_produtor
    }

    assert not divergentes, f"catálogo e produtor declaram bases diferentes: {divergentes}"


def test_o_par_medido_existe_na_fixture(patrimonio: dict, ratios: dict) -> None:
    """Sem ao menos um par casado o teste acima é vacuoso — passaria com zero comparações."""
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets

    e5 = {"patrimonio": patrimonio, "ratios": ratios}
    pares = [
        chave
        for chave, alvo in build_kpi_targets(e5, scoring={}).items()
        if _declaracao_do_produtor(e5, alvo["observado_path"])
    ]

    assert pares, "nenhum kpi_target casou declaração de produtor — gate vacuoso"


def test_cambial_declara_a_base_e_o_catalogo_a_LE(patrimonio: dict) -> None:
    """A 4ª razão: produtor declara, catálogo consome — nenhum dos dois inventa."""
    from pipeline.domain.services.exposicao_cambial_analyzer import compute_exposicao_cambial
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets

    denom = patrimonio["bases"][BaseFinanceira.carteira_financeira_familia.value]["valor_brl"]
    publicado = compute_exposicao_cambial(
        caixa_detalhes=[{"tipo": "caixa_moeda_estrangeira", "moeda": "USD", "valor_brl": 90_000.0}],
        investimentos_atuais=None,
        investivel_financeiro=denom,
    ).to_dict()

    declarada = publicado["base_pct_investivel_financeiro"]
    assert declarada in {b.value for b in BaseFinanceira}
    assert _cents(round(publicado["total_brl"] / denom * 100.0, 2)) == _cents(
        publicado["pct_investivel_financeiro"]
    )
    alvo = build_kpi_targets({"exposicao_cambial": publicado}, scoring={})["exposicao_cambial"]
    assert alvo["base"] == declarada, "catálogo e produtor declaram bases diferentes"


def _enum_de_base() -> set:
    """Vocabulário fechado de `kpi_targets[].base`, lido do schema E5."""
    import json
    from pathlib import Path as _P

    schema = json.loads(
        (_P(__file__).resolve().parents[1] / "config/schemas/e5_analysis.schema.json").read_text()
    )
    return set(
        schema["properties"]["kpi_targets"]["additionalProperties"]["properties"]["base"]["enum"]
    )


# O enum é SINTÁTICO e o recompute é semântico — este teste liga os dois, senão a
# vedação nasce vazia: enum que não cobre o produzido reprovaria em `warn` e ninguém
# veria, e enum derivado do produzido nunca reprovaria nada.
def test_toda_base_produzida_esta_no_enum_do_schema(patrimonio: dict, ratios: dict) -> None:
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets

    e5 = {"patrimonio": patrimonio, "ratios": ratios}
    produzidas = {a["base"] for a in build_kpi_targets(e5, scoring={}).values()}

    assert produzidas, "nenhum alvo produzido — o teste ficaria vacuoso"
    fora = produzidas - _enum_de_base()
    assert not fora, f"base produzida fora do enum: {sorted(fora)}"


# A outra ponta: membro de `BaseFinanceira` que o schema não conhece faria o eixo
# patrimonial publicar base inválida no dia em que um catálogo passasse a citá-lo.
def test_todo_membro_de_BaseFinanceira_cabe_no_enum() -> None:
    from pipeline.domain.services.bases_financeiras import BaseFinanceira

    assert {b.value for b in BaseFinanceira} <= _enum_de_base()
