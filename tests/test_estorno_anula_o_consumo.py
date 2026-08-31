"""[[ADR-429]] F1 — o estorno anula o consumo; hoje ele vira RECEITA.

Fatia de **sinal**, zero linha de produção: a fixture e o gate entram agora, sob
`xfail(strict=True)`. No dia em que o conserto entrar sem remover o xfail, o
`strict` **falha** — o xfail é o gate.

Os invariantes de conservação existentes não pegam isto: são identidades
algébricas sobre o MESMO payload, e detectam total que não fecha com as partes,
nunca lançamento no balde errado. Daí G3, que é o contra-remédio.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from tests.pipeline_golden_substrate import load_fixture, run_e3_e4_e5, write_e5_config

_FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "pipeline_golden" / "e3"
_KEYWORDS = {"lazer_viagens": ["MAGAZINE"]}

#: Os 7 campos que o `financial-planner` fixou como critério de anulação.
_CAMPOS = (
    ("fluxo_caixa", "receita_recorrente"),
    ("fluxo_caixa", "receita_total"),
    ("fluxo_caixa", "despesa_total"),
    ("fluxo_caixa.janela_12m", "despesa_consumo"),
    ("consumo_consciente", "folga_mensal"),
    ("fluxo_caixa.janela_12m", "taxa_poupanca_recorrente"),
    ("consumo_consciente", "total_pontuais"),
)


#: A renda vive SEMPRE no extrato — fatura de cartão não tem salário. Cada mundo é
#: um CONJUNTO de documentos, como no dogfood real. ⚠️ A convenção de sinal é
#: invertida entre os dois (`categorize_transactions.py:733`): em fatura o positivo
#: é COMPRA. Modelar a fatura com sinal de extrato fazia a renda virar despesa e o
#: gate reprovar pelo motivo errado — e, como `xfail(strict)` só reprova quando o
#: teste PASSA, um gate que nunca pode passar nunca sinaliza o conserto.
_MUNDOS = {
    "sem-par": ["estorno-renda"],
    "conta-compra": ["estorno-renda", "estorno-conta-compra"],
    "conta-par": ["estorno-renda", "estorno-conta-par"],
    "fatura-compra": ["estorno-renda", "estorno-fatura-compra"],
    "fatura-par": ["estorno-renda", "estorno-fatura-par"],
    "fatura-pagto": ["estorno-renda", "estorno-fatura-pagto"],
}


def _cenario(tmp_path_factory, nome: str) -> dict:
    root = tmp_path_factory.mktemp(f"estorno_{nome.replace('-', '_')}")
    write_e5_config(root, expense_keywords=_KEYWORDS)
    return run_e3_e4_e5(
        root,
        e3_payloads={doc: load_fixture(_FIX / f"{doc}-3_reconciled.json") for doc in _MUNDOS[nome]},
    )


@pytest.fixture(scope="module")
def mundos(tmp_path_factory) -> dict[str, dict]:
    return {n: _cenario(tmp_path_factory, n) for n in _MUNDOS}


def _leitura(payload: dict) -> dict[str, int]:
    out = {}
    for caminho, campo in _CAMPOS:
        no = payload
        for parte in caminho.split("."):
            no = no.get(parte) or {}
        bruto = no.get(campo)
        out[f"{caminho}.{campo}"] = (
            None if bruto is None else int(Decimal(str(bruto)).quantize(Decimal("0.01")) * 100)
        )
    return out


# G2 vem PRIMEIRO: sem ele, G1 passaria sobre uma fixture em que nada se move.
def test_g2_a_compra_sozinha_move_os_sete(mundos):
    sem_par, so_compra = _leitura(mundos["sem-par"]), _leitura(mundos["conta-compra"])
    movidos = [k for k in sem_par if sem_par[k] != so_compra[k]]
    assert (
        len(movidos) >= 5
    ), f"a compra move só {movidos} — o gate de anulação abaixo passaria por vacuidade"


@pytest.mark.xfail(
    strict=True,
    reason="[[ADR-429]] F1: o conserto é da F2. `strict` faz este xfail VIRAR o gate "
    "no dia em que o estorno parar de ser receita — remover o marker é parte do PR.",
)
@pytest.mark.parametrize("regime", ["fatura-par", "conta-par"])
def test_g1_o_estorno_anula_a_compra(mundos, regime):
    """O controle é o mundo SEM o par (cenário A), não o mundo com a compra."""
    assert _leitura(mundos[regime]) == _leitura(mundos["sem-par"])


# G3 NÃO é xfail: ele já vale hoje, e é isso que o torna útil. É contra-remédio —
# sem ele, G1 seria satisfeito mandando toda linha negativa de fatura para despesa
# negativa, e o PAGAMENTO zeraria a fatura contra si mesma. Marcá-lo `xfail` foi
# erro meu, revelado quando a fixture ganhou a convenção de sinal certa: com ela o
# teste passou, e `xfail(strict)` reprova o que passa.
def test_g3_o_pagamento_da_fatura_nao_e_estorno(mundos):
    com_pagto = _leitura(mundos["fatura-pagto"])
    so_compra = _leitura(mundos["fatura-compra"])
    assert com_pagto["fluxo_caixa.despesa_total"] == so_compra["fluxo_caixa.despesa_total"]


@pytest.mark.xfail(
    strict=True,
    reason="[[ADR-429]]: `_classify_credito` é o único ramo do classificador sem "
    "`abs()`, então receita negativa é publicável. Witness de natureza diferente "
    "dos invariantes de conservação, que passam sobre o payload defeituoso.",
)
@pytest.mark.parametrize("regime", ["fatura-par", "fatura-pagto"])
def test_receita_publicada_nunca_e_negativa(mundos, regime):
    fluxo = mundos[regime]["fluxo_caixa"]
    assert fluxo["receita_total"] >= 0
    assert all(v >= 0 for v in fluxo["por_fonte"].values()), fluxo["por_fonte"]
