"""Núcleo puro do Passo 0 da [[A42.l15]] (`dev/audit_e15_vocab_closure.py`).

A casca de I/O (DB + Fernet) não entra: o que decide o veredito é a
classificação de `codigo` e o fecho de `instituicao` contra o catálogo, e as
duas são puras. Fixtures fabricadas — as formas vêm da medição real de
2026-08-30 (859 artefatos, 10.859 itens), não de invenção.
"""

from __future__ import annotations

import pytest

from dev.audit_e15_vocab_closure import (
    Closure,
    as_dict,
    catalog_tokens,
    classify_codigo,
    report,
    tally,
)


@pytest.mark.parametrize(
    "bruto,esperado",
    [
        ("01", "canonico"),
        (" 41 ", "canonico"),
        ("07-01", "composto"),
        ("06-99", "composto"),
        ("", "ausente"),
        (None, "ausente"),
        ("1", "outra"),
        ("013", "outra"),
        ("abc", "outra"),
    ],
)
def test_classify_codigo(bruto, esperado) -> None:
    assert classify_codigo(bruto) == esperado


def test_catalog_tokens_indexa_code_e_nome() -> None:
    """O LLM emite tanto o code quanto o nome de exibição — os dois contam como fecho."""
    tokens = catalog_tokens({"c6bank": "C6 Bank", "itau": "Itaú"})
    assert "c6bank" in tokens
    assert "itau" in tokens


# `ITAU UNIBANCO S.A.` é a forma que DISCRIMINA exato de substring:
# `normalize("itau")` é substring de `normalize("ITAU UNIBANCO S.A.")`, então um
# match por substring a contaria como fechada e o fecho medido despencaria de
# 43,6% sem nada ter mudado. Sem esta linha a fixture não separa os dois e a
# mutação sobrevive — medido em 2026-08-30, na primeira tentativa deste teste.
_CATALOGO = {"c6bank": "C6 Bank", "itau": "Itaú"}
_EMITIDAS = ["C6 Bank", "BANCO C6", "BANCO C6 S.A.", "ITAU UNIBANCO S.A."]


def test_variante_societaria_conta_como_fora_do_catalogo() -> None:
    """Achado central: o catálogo TEM a instituição e a forma emitida não casa — é gap de
    ALIAS, não de cobertura. Mutação que mata: casar por substring."""
    closure = Closure()
    itens = [{"codigo": "41", "instituicao": nome} for nome in _EMITIDAS]
    tally(itens, catalog_tokens(_CATALOGO), closure)
    assert closure.instituicao_no_catalogo == 1
    assert closure.instituicao_fora == 3


def test_instituicao_ausente_sai_do_denominador() -> None:
    """Item sem `instituicao` não é "fora do catálogo" — é não avaliável."""
    closure = Closure()
    tally([{"codigo": "01"}, {"codigo": "01", "instituicao": ""}], catalog_tokens({}), closure)
    assert closure.instituicao_ausente == 2
    assert closure.instituicao_avaliadas == 0
    assert as_dict(closure, 1, 0, 0)["instituicao_fora_do_catalogo"]["pct"] == 0.0


def test_saida_carrega_numerador_e_denominador() -> None:
    """Percentual sozinho não é auditável — mutação que mata é publicar só `pct`."""
    closure = Closure()
    tally(
        [{"codigo": "01", "instituicao": "Itaú"}, {"codigo": "07-01", "instituicao": "BANCO C6"}],
        catalog_tokens({"itau": "Itaú"}),
        closure,
    )
    data = as_dict(closure, artefatos=3, ilegiveis=1, catalogo=1)
    assert data["codigo_fora_do_canonico"] == {"num": 1, "den": 2, "pct": 50.0}
    assert data["instituicao_fora_do_catalogo"] == {"num": 1, "den": 2, "pct": 50.0}
    assert data["artefatos_ilegiveis"] == 1, "artefato ilegível não pode sumir da conta"


def test_report_nao_soma_extracao_com_agregado() -> None:
    """O defeito que este teste existe para matar: somar `E1.5a` (extração por documento)
    com `E1.5`/`extract_baseline` (agregado que RE-EMITE os mesmos itens) conta cada item
    duas vezes e dilui a taxa da extração com a do agregado — medido em 2026-08-30, a soma
    dava 1,5% quando a extração era 1,86% e o agregado 0,84%, e não descrevia nenhum dos dois."""
    extracao, agregado = Closure(), Closure()
    tally([{"codigo": "01"}, {"codigo": "07-01"}], set(), extracao)
    tally([{"codigo": "01"}, {"codigo": "01"}], set(), agregado)
    data = report({"E1.5a": extracao, "extract_baseline": agregado}, 2, 0, 0)

    assert data["populacao_headline"] == "E1.5a"
    assert data["extracao"]["itens"] == 2, "o headline não pode incluir o agregado"
    assert data["extracao"]["codigo_fora_do_canonico"]["pct"] == 50.0
    assert data["agregado_nao_somar"]["extract_baseline"]["itens"] == 2
    assert "E1.5a" not in data["agregado_nao_somar"], "extração não se repete no agregado"
