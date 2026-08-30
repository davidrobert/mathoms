"""A base do gasto pontual exclui as MESMAS coisas nos produtores que a publicam (A40.l98).

Existiam três produtores de "gasto pontual" com filtros disjuntos, e o que
**prescreve** — o KPI que o parecer ancora — era o que menos filtrava: só
``recorrentes``. O aporte de investimento ([[ADR-333]]: poupança, não consumo)
e a transferência entre contas entravam na base de "gastos pontuais elevados".

A fixture **é** o gate: sem uma linha por motivo, os testes de exclusão passam
sem exercitar nenhum termo em disputa (é o RR6-07 outra vez). Daí
``test_fixture_discrimina_cada_motivo`` vir primeiro.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.domain.services.gasto_pontual_policy import GastoPontualPolicy, VeredictoPontual
from tests.pipeline_golden_substrate import load_fixture, run_e3_e4_e5_ctx, write_e5_config

_FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "pipeline_golden"
_E3 = _FIX / "e3" / "pontuais-com-aporte-3_reconciled.json"

# Load-bearing: sem estas keywords o aluguel deixa de ser `moradia` e a fixture
# mede outro mundo com o mesmo nome (mesma armadilha que a [[A40.l101]] anotou).
_KEYWORDS = {
    "lazer_viagens": ["CINEMA"],
    "aporte_investimento": ["APORTE CDB"],
    "moradia": ["ALUGUEL"],
    "transferencia_familiar": ["PIX FAMILIA"],
}
_PADROES_DE_TRANSFERENCIA = ["CONTA PROPRIA"]

_POLICY = GastoPontualPolicy()


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    root = tmp_path_factory.mktemp("base_pontual")
    write_e5_config(
        root,
        expense_keywords=_KEYWORDS,
        internal_transfer_patterns=_PADROES_DE_TRANSFERENCIA,
    )
    ctx = run_e3_e4_e5_ctx(root, e3_payloads={"pontuais-com-aporte": load_fixture(_E3)})
    return {
        "e4": ctx.artifact_store.read("E4", "despesas")["dados"],
        "e5": ctx.artifact_store.read("E5", "analise_financeira")["consumo_consciente"],
    }


def _valor_por_categoria(dados: dict) -> dict[str, float]:
    return {
        cat: sum(abs(float(t.get("valor", 0))) for t in txs)
        for cat, txs in dados.items()
        if isinstance(txs, list)
    }


def test_fixture_discrimina_cada_motivo(run):
    """Cada motivo do veredito precisa existir na fixture, ACIMA do limiar — senão
    o teste de exclusão correspondente passa sobre um mundo que não o exercita."""
    por_cat = _valor_por_categoria(run["e4"])
    relevante = {c: v for c, v in por_cat.items() if _POLICY.is_relevante(v)}
    faltando = [
        nome
        for nome, cats in (
            ("recorrente", _POLICY.recorrentes),
            ("transferencia_patrimonial", _POLICY.transferencia_patrimonial),
            ("transferencia_de_conta", _POLICY.transferencia_de_conta),
            ("incluido", {"lazer_viagens"}),
            ("nao_identificado", {"nao_identificado"}),
        )
        if not (set(relevante) & set(cats))
    ]
    assert not faltando, (
        f"fixture não exercita: {faltando} — os gates abaixo passariam por vacuidade. "
        f"categorias acima do limiar: {sorted(relevante)}"
    )


def test_transferencia_detectada_nunca_chega_ao_E5(run):
    """Medido, não suposto: o E4 roteia transferência detectada para
    ``kind="transferencia"`` (passo 1 do classificador) e ela não entra em
    ``despesas.dados``. Filtro de detector dentro do ``_collect_candidates``
    seria inerte por construção — é por isso que ele não existe lá."""
    descricoes = [t.get("descricao", "") for txs in run["e4"].values() for t in txs]
    assert not [d for d in descricoes if "CONTA PROPRIA" in d]
    assert not [i for i in run["e5"]["itens"] if "CONTA PROPRIA" in i["descricao"]]


@pytest.mark.parametrize(
    "motivo,categorias",
    [
        ("recorrente", _POLICY.recorrentes),
        ("transferencia_por_categoria", _POLICY.nao_consumo_pontual),
    ],
)
def test_base_publicada_exclui_por_natureza(run, motivo, categorias):
    intrusos = [i for i in run["e5"]["itens"] if i["categoria"] in categorias]
    assert not intrusos, f"{motivo} na base do pontual: {intrusos}"


def test_delta_por_causa_e_atribuivel(run):
    """A base publicada + o que cada causa retirou reconstrói o bruto — o delta é
    declarado POR CAUSA, não como um total agregado que esconde a atribuição."""
    por_cat = _valor_por_categoria(run["e4"])
    acima = {c: v for c, v in por_cat.items() if _POLICY.is_relevante(v)}
    publicado = sum(i["valor"] for i in run["e5"]["itens"])

    patrimonial = sum(v for c, v in acima.items() if c in _POLICY.transferencia_patrimonial)
    de_conta = sum(v for c, v in acima.items() if c in _POLICY.transferencia_de_conta)
    nao_classificado = sum(v for c, v in acima.items() if c in _POLICY.nao_classificadas)
    assert patrimonial == 12_000.0
    assert de_conta == 4_000.0
    assert nao_classificado == 7_000.0
    assert publicado == pytest.approx(39_000.0)
    assert publicado + patrimonial + de_conta + nao_classificado == pytest.approx(62_000.0)


def test_nao_identificado_sai_do_numerador_mas_fica_no_inventario(run):
    """[[ADR-425]] §D1 — o não classificado é ausência de MEDIÇÃO, não ruído. Sai
    do numerador que sustenta conselho; o inventário o mantém, com total e
    contagem, senão a família não tem como agir sobre ele."""
    consumo = run["e5"]
    assert not [i for i in consumo["itens"] if i["categoria"] in _POLICY.nao_classificadas]
    balde = consumo["base_pontuais"]["excluidos"]["nao_identificado"]
    assert balde == {"valor": 7_000.0, "contagem": 1}


def test_o_leitor_soma_os_itens_e_chega_ao_total(run):
    """`itens` acompanha `publicado`: par publicado que o leitor não recompõe é a
    doença que a A40.l101 anotou no denominador."""
    consumo = run["e5"]
    assert sum(i["valor"] for i in consumo["itens"]) == pytest.approx(consumo["total_pontuais"])


# ---------------------------------------------------------------------------
# `base_pontuais` — [[ADR-425]] §D2
# ---------------------------------------------------------------------------


def test_a_base_conserva(run):
    """``bruto == publicado + Σ excluidos`` — sem a identidade, um balde pode
    sumir e o leitor não tem como notar."""
    base = run["e5"]["base_pontuais"]
    soma = base["publicado"]["valor"] + sum(b["valor"] for b in base["excluidos"].values())
    contagem = base["publicado"]["contagem"] + sum(
        b["contagem"] for b in base["excluidos"].values()
    )
    assert base["bruto"]["valor"] == pytest.approx(soma)
    assert base["bruto"]["contagem"] == contagem


def test_o_publicado_e_o_total_pontuais(run):
    """O objeto não é um segundo número ao lado do KPI: é a decomposição DELE."""
    assert run["e5"]["base_pontuais"]["publicado"]["valor"] == pytest.approx(
        run["e5"]["total_pontuais"]
    )


def test_todo_balde_excluido_tem_veredito_conhecido(run):
    """Chave fora do enum fechado quebra o rótulo do leitor em silêncio."""
    vereditos = {v.value for v in VeredictoPontual} - {VeredictoPontual.incluido.value}
    assert set(run["e5"]["base_pontuais"]["excluidos"]) <= vereditos


def test_a_base_nao_esconde_o_que_o_bruto_inclui(run):
    """O universo é *todo lançamento ≥ limiar*. Um `bruto` mais estreito seria ele
    próprio um filtro não declarado — o defeito que esta base existe para remover."""
    acima = sum(
        abs(float(t.get("valor", 0)))
        for txs in run["e4"].values()
        for t in txs
        if _POLICY.is_relevante(abs(float(t.get("valor", 0))))
    )
    assert run["e5"]["base_pontuais"]["bruto"]["valor"] == pytest.approx(acima)
