"""Testes do detector de orçamento de relógio em `dev/check_test_health.py`.

Cada caso reproduz uma forma real: a que quebrou em
`test_upsert_invalidates_cache_within_100ms` (143 ms contra teto de 100) e a
que vivia em `test_vetorizacao_10k_menos_de_2s`.
"""

from __future__ import annotations

import ast

from dev.check_test_health import _find_wallclock_budget_assert


def _achados(source: str) -> list[tuple[int, str]]:
    return _find_wallclock_budget_assert(ast.parse(source), source)


def test_elapsed_ms_contra_literal_e_pego() -> None:
    fonte = (
        "import time\n"
        "def test_x():\n"
        "    t0 = time.monotonic()\n"
        "    agir()\n"
        "    elapsed_ms = (time.monotonic() - t0) * 1000.0\n"
        "    assert elapsed_ms < 100.0\n"
    )
    assert len(_achados(fonte)) == 1


def test_orcamento_escondido_em_and_e_pego() -> None:
    """A forma exata do caso de origem: `assert override_id and elapsed_ms < 100.0`."""
    fonte = (
        "import time\n"
        "def test_x():\n"
        "    t0 = time.monotonic()\n"
        "    ok = agir()\n"
        "    elapsed_ms = (time.monotonic() - t0) * 1000.0\n"
        "    assert ok and elapsed_ms < 100.0, 'msg'\n"
    )
    assert len(_achados(fonte)) == 1


def test_subtracao_de_dois_relogios_e_pega() -> None:
    """Nenhuma linha lê relógio E compara — a derivação precisa propagar por nome."""
    fonte = (
        "from time import perf_counter\n"
        "def test_x():\n"
        "    t0 = perf_counter()\n"
        "    agir()\n"
        "    t1 = perf_counter()\n"
        "    d = t1 - t0\n"
        "    assert d < 1\n"
    )
    assert len(_achados(fonte)) == 1


def test_marker_perf_e_a_valvula_de_escape() -> None:
    fonte = (
        "import time\n"
        "import pytest\n"
        "@pytest.mark.perf\n"
        "def test_x():\n"
        "    t0 = time.monotonic()\n"
        "    agir()\n"
        "    assert (time.monotonic() - t0) < 1.0\n"
    )
    assert _achados(fonte) == []


def test_campo_chamado_duration_nao_e_relogio() -> None:
    """`duration_ms` de um StageResult é dado, não medição — 40+ testes o comparam."""
    fonte = (
        "def test_x():\n"
        "    result = agir()\n"
        "    assert result.duration_ms == 7.0\n"
        "    assert result.duration_ms < 5000\n"
    )
    assert _achados(fonte) == []


def test_lista_de_janelas_em_segundos_nao_e_relogio() -> None:
    fonte = (
        "def test_x():\n"
        "    janelas = agir()\n"
        "    assert janelas == [60, 300, 900, 3600, 3600]\n"
    )
    assert _achados(fonte) == []
