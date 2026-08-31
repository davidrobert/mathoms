"""[[ADR-430]] — valor impossível em ativo físico vira `null` declarado.

O eixo de não-inércia destes testes é o par `secao == "bens_direitos"` **com**
negativo. Fixture que exercite só o ramo do sinal já passava antes da mudança:
sem `secao`, o classificador ([[ADR-394]] D1) roteia o item para o passivo pelo
sinal, ele nunca chega a `imoveis_consolidados`, e o defeito não se reproduz.
`test_o_ramo_do_sinal_nao_reproduz_o_defeito` é o controle que fixa isso.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from datetime import date
from decimal import Decimal

import pytest

from pipeline.domain.services.carteira_por_papel import build_carteira_por_papel
from pipeline.domain.services.patrimonio_calculator import PatrimonioCalculator
from pipeline.domain.services.patrimonio_resolvers import resolve_members
from pipeline.domain.services.patrimonio_types import (
    MemberIdentity,
    PatrimonioConfig,
    PatrimonioInputs,
)
from pipeline.domain.services.real_estate_metrics import (
    MOTIVO_VALOR_NAO_APURADO,
    BenchmarkRates,
    PropertyInput,
    calculate_real_estate_metrics,
    filter_investment_properties,
)
from pipeline.domain.services.valor_nao_apurado import sanear_baseline
from scripts.consolidate_baseline import consolidate_from_itens

_IDENT = MemberIdentity(titular_key="david", conjuge_key="", titular_nome="David", conjuge_nome="")
_CASA_BRL = Decimal("1000000")
_APTO_OK_BRL = Decimal("300000")
_SALDO_DEVEDOR_BRL = Decimal("-150000")


# `Decimal` em memória; `float` só no payload, que é JSON do E1.5a ([[ADR-090]]).
def _item(descricao: str, quantia: Decimal, *, secao: str | None = "bens_direitos") -> dict:
    item = {
        "codigo": "11",
        "descricao": descricao,
        "categoria_hint": "imovel",
        "valor_brl": float(quantia),
        "membro": "david",
        "ano": 2025,
        "instituicao": "Banco X",
    }
    if secao is not None:
        item["secao"] = secao
    return item


def _consolidar(*itens: dict) -> dict:
    with redirect_stdout(io.StringIO()):
        return consolidate_from_itens({"resumo": {"ano_referencia": 2025}, "itens": list(itens)})


def _patrimonio(baseline: dict) -> dict:
    inputs = PatrimonioInputs(
        baseline=baseline,
        members=resolve_members(baseline, _IDENT),
        carteira=build_carteira_por_papel(None, titular_key="david", conjuge_key=""),
    )
    with redirect_stdout(io.StringIO()):
        return PatrimonioCalculator(PatrimonioConfig(members=_IDENT)).calculate(inputs)


@pytest.fixture
def baseline_com_apto_negativo() -> dict:
    """O par que reproduz: `secao` decide o eixo, e o valor é impossível."""
    return _consolidar(_item("APTO 101", _SALDO_DEVEDOR_BRL), _item("CASA", _CASA_BRL))


@pytest.fixture
def baseline_corrigido() -> dict:
    """Mesmo corpus com o valor do apartamento apurado — contra-prova."""
    return _consolidar(_item("APTO 101", _APTO_OK_BRL), _item("CASA", _CASA_BRL))


# =============================================================================
# Não-inércia — o par (secao, negativo) é o que muda de comportamento
# =============================================================================


def test_o_ramo_do_sinal_nao_reproduz_o_defeito():
    # Controle da não-inércia: uma fixture escrita só com o negativo, sem o fato
    # de eixo, passa igualmente antes e depois da [[ADR-430]] e não prova nada.
    """Sem `secao`, o sinal roteia para o passivo e nada chega ao ativo."""
    baseline = _consolidar(_item("APTO 101", _SALDO_DEVEDOR_BRL, secao=None))

    assert baseline["imoveis_consolidados"] == []
    assert len(baseline["dividas"]) == 1


def test_secao_com_negativo_chega_ao_ativo_e_e_saneado(baseline_com_apto_negativo):
    """Com `secao`, o item entra no ativo — e é ali que a ADR age."""
    apto = baseline_com_apto_negativo["imoveis_consolidados"][0]

    assert apto["eixo_autoridade"] == "secao"
    assert apto["valores_31_12"]["2025"] is None
    assert apto["valor_nao_apurado"]["anos"] == ["2025"]
    assert baseline_com_apto_negativo["dividas"] == []


# =============================================================================
# Critério 1 — nenhum item físico publica valor negativo
# =============================================================================


@pytest.mark.parametrize("colecao", ["imoveis_consolidados", "veiculos_consolidados"])
def test_nenhum_item_fisico_publica_valor_negativo(colecao):
    baseline = {colecao: [{"descricao": "X", "valores_31_12": {"2025": -1.0, "2024": 10.0}}]}
    sanear_baseline(baseline)
    valores = baseline[colecao][0]["valores_31_12"]

    assert valores["2025"] is None
    assert valores["2024"] == 10.0, "ano apurado não é tocado"


def test_review_reason_nomeia_ano_e_colecao(baseline_com_apto_negativo):
    razoes = baseline_com_apto_negativo["imoveis_consolidados"][0]["review_reasons"]
    razao = next(r for r in razoes if r["code"] == "domain.valor_nao_apurado")

    assert "2025" in razao["offending_value"]
    assert "imoveis_consolidados" in razao["offending_value"]


def test_saneamento_e_idempotente(baseline_com_apto_negativo):
    """Roda no item e no boundary do stage — reentrar não pode duplicar razão."""
    antes = len(baseline_com_apto_negativo["imoveis_consolidados"][0]["review_reasons"])
    sanear_baseline(baseline_com_apto_negativo)

    assert len(baseline_com_apto_negativo["imoveis_consolidados"][0]["review_reasons"]) == antes


def test_valor_impossivel_nao_reentra_pelo_agregado(baseline_com_apto_negativo):
    """`patrimonio_por_ano` é o resíduo que o E5 credita ao titular ([[ADR-394]] D8)."""
    assert baseline_com_apto_negativo["patrimonio_por_ano"]["2025"]["total_bens"] == float(
        _CASA_BRL
    )


# =============================================================================
# Critério 3 — Σ exclui o item nulo e os agregados seguem consistentes
# =============================================================================


def test_soma_exclui_o_item_nulo(baseline_com_apto_negativo):
    patrimonio = _patrimonio(baseline_com_apto_negativo)

    assert patrimonio["bruto"] == float(_CASA_BRL)


def test_composicao_identica_ao_bruto(baseline_com_apto_negativo):
    patrimonio = _patrimonio(baseline_com_apto_negativo)
    soma = sum(linha["valor"] for linha in patrimonio["composicao"])

    assert round(soma, 2) == patrimonio["bruto"]
    assert patrimonio["liquido"] == patrimonio["bruto"] - patrimonio["dividas"]


def test_o_item_fica_no_inventario_sem_valor(baseline_com_apto_negativo):
    """Apagar o item esconderia um bem da família; o que sai é o VALOR."""
    baseline = baseline_com_apto_negativo
    inputs = PatrimonioInputs(
        baseline=baseline,
        members=resolve_members(baseline, _IDENT),
        carteira=build_carteira_por_papel(None, titular_key="david", conjuge_key=""),
    )
    imoveis = inputs.members.titular["bens"]["imoveis"]
    apto = next(i for i in imoveis if i["descricao"].startswith("APTO"))

    assert len(imoveis) == 2
    assert apto["valor_31_12_ano_base"] is None, "null, nunca 0,0 ([[ADR-346]])"
    assert apto["valor_nao_apurado"] is True


# =============================================================================
# Critério 4 — a prescrição sai suprimida com motivo declarado
# =============================================================================


def test_prescricao_suprimida_com_motivo_declarado(baseline_com_apto_negativo):
    guarda = _patrimonio(baseline_com_apto_negativo)["guarda_de_sinal"]

    assert guarda["cobertura_completa"] is False
    assert "valor_nao_apurado" in guarda["motivo_supressao"]
    assert guarda["itens_sem_valor"][0]["colecao"] == "imoveis"


def test_descritivo_publica_inteiro(baseline_com_apto_negativo):
    """Suprimir a descrição esconde o defeito onde o leitor confere ([[ADR-394]])."""
    patrimonio = _patrimonio(baseline_com_apto_negativo)

    assert patrimonio["bruto"] > 0
    assert patrimonio["composicao"]


# =============================================================================
# Critério 5 — contra-prova de reversibilidade
# =============================================================================


def test_item_corrigido_volta_a_publicar_a_prescricao(baseline_corrigido):
    patrimonio = _patrimonio(baseline_corrigido)

    assert patrimonio["bruto"] == float(_CASA_BRL + _APTO_OK_BRL)
    assert patrimonio["guarda_de_sinal"]["cobertura_completa"] is True
    assert patrimonio["guarda_de_sinal"]["motivo_supressao"] is None
    assert patrimonio["guarda_de_sinal"]["itens_sem_valor"] == []


def test_a_supressao_nao_e_permanente(baseline_com_apto_negativo, baseline_corrigido):
    """O mesmo corpus, um número trocado: a ressalva some e a prescrição volta."""
    com_defeito = _patrimonio(baseline_com_apto_negativo)["guarda_de_sinal"]
    corrigido = _patrimonio(baseline_corrigido)["guarda_de_sinal"]

    assert com_defeito["cobertura_completa"] != corrigido["cobertura_completa"]


# =============================================================================
# Critério 6 (S4) — fora do cap rate e do peso da carteira
# =============================================================================


def _prop(pid: str, valor: str, *, nao_apurado: bool = False) -> PropertyInput:
    return PropertyInput(
        property_id=pid,
        descricao=pid,
        classification="locado",
        valor_imovel=Decimal(valor),
        aluguel_bruto_anual=Decimal("36000"),
        valor_nao_apurado=nao_apurado,
    )


def test_imovel_sem_valor_sai_do_filtro_com_motivo():
    incluidos, excluidos = filter_investment_properties(
        [_prop("sem-valor", "0", nao_apurado=True), _prop("medido", "500000")]
    )

    assert [p.property_id for p in incluidos] == ["medido"]
    assert excluidos[0].motivo == MOTIVO_VALOR_NAO_APURADO


def test_valor_nao_apurado_vence_a_classificacao():
    """Imóvel de investimento sem valor não pode entrar como se fosse medido."""
    prop = PropertyInput(
        property_id="p",
        descricao="p",
        classification="locado",
        valor_imovel=Decimal("0"),
        valor_nao_apurado=True,
    )
    incluidos, excluidos = filter_investment_properties([prop])

    assert incluidos == []
    assert len(excluidos) == 1


def test_cap_rate_nao_conta_o_imovel_sem_valor():
    """O denominador é só a parte medida da carteira ([[ADR-430]] §Consequências)."""
    benchmarks = BenchmarkRates(
        cdi_liquido_pct=Decimal("8"),
        ntnb_liquido_pct=Decimal("6"),
        ifix_yield_pct=Decimal("8"),
        as_of_date=date(2025, 12, 31),
    )
    so_medido = calculate_real_estate_metrics(
        [_prop("medido", "500000")], Decimal("10"), benchmarks
    )
    com_orfao = calculate_real_estate_metrics(
        [_prop("medido", "500000"), _prop("sem-valor", "0", nao_apurado=True)],
        Decimal("10"),
        benchmarks,
    )

    assert com_orfao.cap_rate_bruto_pct == so_medido.cap_rate_bruto_pct
    assert com_orfao.valor_total_imoveis == so_medido.valor_total_imoveis
