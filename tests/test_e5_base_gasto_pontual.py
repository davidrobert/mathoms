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

import re
from decimal import Decimal
from pathlib import Path

import pytest

from pipeline.domain.services.consumo_consciente_calculator import BaldePontual, BasePontuais
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


def _cents(publicado: object) -> int:
    """O número como o wire o entrega (JSON `number`), em cents int — a única
    unidade em que a identidade é comparável sem erro de float ([[ADR-090]])."""
    return int(Decimal(str(publicado)).quantize(Decimal("0.01")) * 100)


@pytest.mark.parametrize(
    "publicado,excluido",
    [("100.005", "200.005"), ("1.115", "2.225"), ("0.005", "0.004")],
)
def test_a_identidade_fecha_no_WIRE_e_nao_so_no_acumulador(publicado, excluido):
    """Em cents EXATOS, sem ``approx``. O acumulador é ``Decimal``, mas quem lê o
    payload soma os valores **publicados**: somar cru antes de arredondar publicava
    ``300,01`` ao lado de ``100,00 + 200,00``. ``approx(rel=1e-6)`` sobre os
    R$ 394 mil do dogfood dá R$ 0,39 de folga e não veria isso."""
    base = BasePontuais(
        BaldePontual(Decimal(publicado), 1), {"recorrente": BaldePontual(Decimal(excluido), 1)}
    )
    d = base.to_dict()
    soma = _cents(d["publicado"]["valor"]) + sum(
        _cents(b["valor"]) for b in d["excluidos"].values()
    )
    assert _cents(d["bruto"]["valor"]) == soma


def test_a_base_conserva(run):
    """``bruto == publicado + Σ excluidos`` sobre o payload REAL, em cents exatos."""
    base = run["e5"]["base_pontuais"]
    soma = _cents(base["publicado"]["valor"]) + sum(
        _cents(b["valor"]) for b in base["excluidos"].values()
    )
    contagem = base["publicado"]["contagem"] + sum(
        b["contagem"] for b in base["excluidos"].values()
    )
    assert _cents(base["bruto"]["valor"]) == soma
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


def test_o_caminho_sem_detector_e_ESCOLHIDO_nao_herdado():
    """Não existe assinatura em que o filtro mais permissivo seja alcançável por
    OMISSÃO. Um `detector=None` default faria um produtor novo receber a
    classificação frouxa sem pedir — a forma exata do defeito que esta lane mata,
    promovida a propriedade da API."""
    assert not hasattr(_POLICY, "classify")
    descricao = "TED PARA CONTA PROPRIA ITAU"
    assert _POLICY.classify_por_categoria("lazer_viagens") is VeredictoPontual.incluido

    class _DetectorSempre:
        def is_internal_transfer(self, description: str, *, banco: str = "") -> bool:
            return True

    assert (
        _POLICY.classify_com_detector(
            "lazer_viagens", descricao=descricao, banco="itau", detector=_DetectorSempre()
        )
        is VeredictoPontual.transferencia_detectada
    )


# ---------------------------------------------------------------------------
# `cobertura_nivel` — [[ADR-425]] §Emenda, régua da [[ADR-353]] D1
# ---------------------------------------------------------------------------


def test_a_regua_e_IMPORTADA_da_adr353_e_tem_sitio_unico():
    """Igualdade de valor não prova não-redeclaração: um `30.0` copiado passaria.
    O gate conta os SÍTIOS de definição em `pipeline/domain/services/`."""
    raiz = Path(__file__).resolve().parents[1] / "pipeline" / "domain" / "services"
    for nome in ("NAO_IDENTIFICADO_PARCIAL_PCT", "NAO_IDENTIFICADO_INSUFICIENTE_PCT"):
        sitios = [
            f.name
            for f in raiz.glob("*.py")
            if re.search(rf"^{nome}\s*=", f.read_text(encoding="utf-8"), re.M)
        ]
        assert sitios == [
            "diagnostico_comportamental_analyzer.py"
        ], f"{nome} definida em {sitios} — a régua tem de ter sítio único"


def test_a_fixture_discrimina_as_DUAS_razoes(run):
    """Anti-vacuidade: com `recorrente`/`transferencia_*` zerados, `publicado/bruto`
    e `publicado/(publicado+nao_identificado)` COINCIDEM, e todo gate de nível passa
    sem exercitar a escolha do denominador."""
    base = run["e5"]["base_pontuais"]
    pub = base["publicado"]["valor"]
    medivel = pub + base["excluidos"]["nao_identificado"]["valor"]
    assert pub / base["bruto"]["valor"] != pytest.approx(pub / medivel, rel=1e-3)


@pytest.mark.parametrize(
    "publicado,nao_identificado,esperado",
    [("95", "5", "alta"), ("80", "20", "parcial"), ("50", "50", "insuficiente")],
)
def test_os_tres_niveis(publicado, nao_identificado, esperado):
    base = BasePontuais(
        BaldePontual(Decimal(publicado), 1),
        {"nao_identificado": BaldePontual(Decimal(nao_identificado), 1)},
    )
    assert base.to_dict()["cobertura_nivel"] == esperado


def test_sem_base_medivel_o_nivel_e_null_com_motivo():
    """`alta` sobre medição que não houve é afirmação sobre o dinheiro da família
    ([[ADR-394]] §D7) — diverge da [[ADR-353]] D2 de propósito."""
    d = BasePontuais(BaldePontual(), {}).to_dict()
    assert d["cobertura_nivel"] is None
    assert d["cobertura_motivo"].startswith("sem_base_medivel:")


# ---------------------------------------------------------------------------
# Vocabulário da policy — todo código ou é produzível, ou é DECLARADO defensivo
# ---------------------------------------------------------------------------

#: Não produzidos por nenhum produtor (medido 2026-08-31): ausentes do seed canônico,
#: de `_HINTS_DESPESA` e de `default_expense_category`. `transferencias_internas` nem
#: é categoria — é o nome do BLOCO em `family_members.json`. Existem contra
#: `workspace_category_overrides`, que pode criar categoria arbitrária.
_DEFENSIVOS = {"transferencia_entre_contas", "transferencia_familiar", "transferencias_internas"}


def _categorias_produziveis() -> set[str]:
    """O universo é a UNIÃO das quatro fontes que emitem categoria de despesa —
    definido pelo que ele É, não pelo que faz a policy passar. Recortá-lo depois de
    conhecer o ofensor produziria gate que aprova a si mesmo."""
    raiz = Path(__file__).resolve().parents[1]
    fontes = {
        "seed": raiz / "backend/alembic/versions/a5b6c7d8e9f0_seed_category_template_v1.py",
        "hints_llm": raiz / "pipeline/domain/services/llm_category_hint.py",
        "labels_pj": raiz / "pipeline/domain/services/transaction_classifier_pj.py",
        "classificador": raiz / "pipeline/domain/services/transaction_classifier.py",
    }
    faltando = [n for n, f in fontes.items() if not f.exists()]
    assert not faltando, f"fonte do universo sumiu — re-meça: {faltando}"
    universo: set[str] = set()
    for f in fontes.values():
        universo |= set(re.findall(r'"([a-z][a-z0-9_]{2,})"', f.read_text(encoding="utf-8")))
    return universo


def test_todo_codigo_da_policy_e_produzivel_ou_declarado_defensivo():
    """Sem este gate o próximo conjunto nasce fantasma igual: a `transferencia_de_conta`
    passou meses parecendo decisão de domínio sobre códigos que nada emite, enquanto o
    código REAL de dinheiro à família (`suporte_familiar`) ficava `incluido` e entrava
    12× em `total_pontuais`."""
    semeadas = _categorias_produziveis()
    # Anti-vacuidade: se o universo virasse vazio ou largo demais, o gate aprovaria
    # tudo. Estas duas âncoras fixam que ele é POVOADO e ainda assim DISCRIMINA.
    assert "suporte_familiar" in semeadas, "o universo perdeu o seed — re-meça"
    assert "transferencia_familiar" not in semeadas, (
        "o universo ficou largo demais: ele passou a conter um código que nenhum "
        "produtor emite, e o gate deixaria fantasma novo entrar"
    )
    declarados = set(_POLICY.recorrentes) | set(_POLICY.nao_consumo_pontual)
    fantasmas = {c for c in declarados if c not in semeadas} - _DEFENSIVOS
    assert not fantasmas, (
        f"código na policy que nenhum produtor emite e não está declarado defensivo: "
        f"{sorted(fantasmas)}"
    )


def test_suporte_familiar_e_recorrente_e_NAO_transferencia():
    """A colocação é load-bearing: em `recorrentes` ele sai só da base do pontual; em
    `transferencia_patrimonial` sairia de `despesa_consumo` e moveria a taxa de
    poupança — e sustento a familiar É consumo."""
    assert _POLICY.classify_por_categoria("suporte_familiar") is VeredictoPontual.recorrente
    assert "suporte_familiar" not in _POLICY.nao_consumo_pontual
