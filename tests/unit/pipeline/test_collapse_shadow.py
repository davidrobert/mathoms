"""Sombra do colapso cross-documento em produção (ADR-364 · A40.l2 PR3a).

O que estes testes travam é a propriedade que torna a sombra *shipável*: ela mede sem
mudar nada. Um teste que só checasse "o colapsador foi instanciado" passaria igual se
`collapse_enforce` vazasse para True — e aí a sombra removeria dado em produção.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.cross_document_collapse_types import (  # noqa: E402
    shadow_counts,
)
from tests.unit.pipeline.test_collapse_cardinality import _doc, _measure  # noqa: E402


def _duas_pernas():
    """Mesma chave em duas proveniências — o caso que a lane existe para medir."""
    return [_doc(1, "itau_extrato.json"), _doc(1, "itau_llm.json", metodo="llm")]


def test_measure_nao_muda_a_lista_de_statements():
    """A sombra não pode ter caminho de escrita — nem por acidente de aliasing."""
    stmts = _duas_pernas()
    antes = [(s.source_document, len(s.transactions)) for s in stmts]

    candidates = _measure(stmts)

    assert [(s.source_document, len(s.transactions)) for s in stmts] == antes
    assert any(c.collapsible for c in candidates), "fixture sem candidato não prova nada"


def test_shadow_counts_conta_so_o_colapsavel():
    counts = shadow_counts(_measure(_duas_pernas()))

    assert counts["candidatos"] == 1
    assert counts["colapsaveis"] == 1
    assert counts["rows_removiveis"] == 1
    # `valor_cents` é MAGNITUDE — o sinal vive em `direction`, como no instrumento da
    # A40.l1. Somar com sinal aqui faria débito e crédito se cancelarem no agregado.
    assert counts["cents_removiveis"] == 10_000


def test_shadow_counts_materializa_generator():
    """Regressão: consumir o iterador na comprehension reportaria ``candidatos=0``."""
    candidates = _measure(_duas_pernas())

    counts = shadow_counts(c for c in candidates)

    assert counts["candidatos"] == 1


def test_bloqueado_conta_como_candidato_mas_nao_como_colapsavel():
    """Partição: o agregado não pode confundir "vi" com "removeria"."""
    # Duas nativas de arquivos distintos: candidato de UMA proveniência, nada a remover
    # (D5 — row nativa nunca sai).
    counts = shadow_counts(_measure([_doc(1, "a.json"), _doc(1, "b.json")]))

    assert counts["colapsaveis"] == 0
    assert counts["rows_removiveis"] == 0


@pytest.mark.parametrize("campo", ["candidatos", "colapsaveis", "rows_removiveis"])
def test_sem_candidato_zera_sem_estourar(campo):
    assert shadow_counts(())[campo] == 0
