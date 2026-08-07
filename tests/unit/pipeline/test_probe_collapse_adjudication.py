"""Guard anti-vácuo + classificação fail-closed do probe de adjudicação ([[A40.l2]]).

A 1ª execução deste probe imprimiu `adjudicação por hash MORTA` com corpus vazio — o
instrumento não capturara statement nenhum. Publicar aquele zero teria matado um desenho
correto. O que estes testes travam é a distinção entre `0` por "não observei" e `0` por
"observei e não achei"; um teste que só conferisse as contagens não a alcança.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dev.probe_collapse_adjudication import (  # noqa: E402
    _classificar,
    _emitir,
    _join_vivo,
)


class _Override:
    def __init__(self, *, natural=None, tx=None, versao=2):
        self.natural_key_hash = natural
        self.transaction_hash = tx
        self.hash_version = versao


def _classes(**kwargs) -> Counter:
    return Counter(kwargs)


def test_corpus_vazio_e_indeterminado_nao_veredito():
    assert _emitir(_classes(), corpus=set(), ativos=[object()]) == 2


def test_sem_override_e_indeterminado():
    assert _emitir(_classes(), corpus={"a"}, ativos=[]) == 2


def test_com_corpus_e_override_emite_veredito():
    assert _emitir(_classes(casou_nada=1), corpus={"a"}, ativos=[object()]) == 0


def test_join_vivo_conta_match_fora_de_candidato():
    """Distinção que a 1ª versão perdeu: casar corpus é join vivo, mesmo sem candidato."""
    assert _join_vivo(_classes(casou_corpus_fora_de_candidato=1)) is True
    assert _join_vivo(_classes(casou_nada=3, sem_v2=2)) is False


@pytest.mark.parametrize(
    ("override", "esperado"),
    [
        (_Override(natural="s1"), "casou_sobrevivente"),
        (_Override(natural="r1"), "casou_removido"),
        (_Override(natural="c1"), "casou_corpus_fora_de_candidato"),
        (_Override(natural="zzz"), "casou_nada"),
        (_Override(natural="s1", versao=1), "sem_v2"),
        (_Override(), "casou_nada"),
    ],
)
def test_classificacao_e_fail_closed(override, esperado):
    """Desconhecido nunca é 'seguro' — v1 e âncora ausente caem em classe própria."""
    assert _classificar(override, {"s1"}, {"r1"}, {"s1", "r1", "c1"}) == esperado


def test_transaction_hash_serve_de_ancora_quando_natural_falta():
    """Override pré-v2-natural ainda pode ancorar — ignorar isso subconta o risco."""
    assert _classificar(_Override(tx="r1"), {"s1"}, {"r1"}, {"r1"}) == "casou_removido"
