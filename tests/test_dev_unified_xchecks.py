"""Controle positivo da guarda anti-vacuo dos cross-checks da rodada unificada.

A regra vem do §10 do `U2` (item 2) e reprovou de novo no `U3`: um check que
compara **zero** celulas e imprime ✅ — ou que imprime 647 divergencias sobre uma
intersecao vazia — nao e veredito. A guarda mora no FORMATO de saida, e um check
sem controle positivo que dispara nao pode ser confiado (§10 `U2`, item 1).
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout

import pytest

from dev._unified_xchecks.base import _cents, veredito


def _saida(n_comparado: int, n_esperado: int, divergentes: int) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        veredito("CTRL", n_comparado, n_esperado, divergentes)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("n_comparado", "n_esperado", "divergentes", "esperado"),
    [
        (0, 10, 0, "INAPLICAVEL"),
        (3, 10, 0, "INAPLICAVEL"),
        (10, 10, 0, "FECHA"),
        (10, 10, 2, "DIVERGE"),
        (0, 10, 647, "INAPLICAVEL"),
    ],
)
def test_veredito_discrimina(n_comparado, n_esperado, divergentes, esperado):
    assert esperado in _saida(n_comparado, n_esperado, divergentes)


def test_vacuo_nunca_sai_verde():
    """O caso que enganou o `U3`: divergencia alta sobre populacao vazia."""
    saida = _saida(0, 1540, 647)
    assert "FECHA" not in saida and "DIVERGE" not in saida


def test_par_de_denominadores_sempre_publicado():
    """`n_comparado` e `n_esperado` na MESMA linha do veredito, em todo caso."""
    for args in ((0, 10, 0), (3, 10, 0), (10, 10, 0), (10, 10, 2)):
        saida = _saida(*args)
        assert f"n_comparado={args[0]}" in saida
        assert f"n_esperado={args[1]}" in saida


def test_cents_nao_confunde_bool_com_numero():
    assert _cents(True) is None
    assert _cents(None) is None
    assert _cents("1.23") == 123
    assert _cents(0) == 0
