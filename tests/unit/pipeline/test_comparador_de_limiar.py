"""Veredito do comparador — o que a tabela do parecer pode afirmar (A40.l92).

O caso de origem: `taxa_endividamento` 45% contra `≤ 20%` desenhava trilha 100% cheia,
porque o front fazia `clamp(atual / alvo)` sem saber a direção. O veredito sai daqui,
sobre o bruto, e o teto nunca tem progresso.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.comparador_de_limiar import (
    VereditoDoComparador,
    veredito_do_comparador,
)


def test_teto_violado_nao_tem_progresso():
    assert veredito_do_comparador(45.0, "<=", 20.0) == VereditoDoComparador("<=", False, None)


@pytest.mark.parametrize("observado", [10.0, 20.0])
def test_teto_conforme_inclusive_no_limiar_exato(observado):
    """O limiar é o último valor conforme ([[ADR-399]] §Emenda 2026-10-08)."""
    assert veredito_do_comparador(observado, "<=", 20.0) == VereditoDoComparador("<=", True, None)


def test_piso_atingido_e_100():
    assert veredito_do_comparador(6.0, ">=", 6.0) == VereditoDoComparador(">=", True, 100)


# 5,6 contra 6 é 93% — a barra que a 12px se lê "atingido", e por isso o status existe.
def test_piso_abaixo_publica_progresso_arredondado_para_baixo():
    assert veredito_do_comparador(5.6, ">=", 6.0) == VereditoDoComparador(">=", False, 93)


def test_progresso_e_decimal_nao_float():
    """Em float, floor(0,29 × 100) dá 28 — o erro que o Decimal existe para evitar."""
    assert veredito_do_comparador(0.29, ">=", 1.0).progresso_pct == 29


def test_100_so_se_conforme_mesmo_a_um_fio_do_limiar():
    assert veredito_do_comparador(5.9999, ">=", 6.0).progresso_pct == 99


def test_piso_negativo_nao_publica_progresso_negativo():
    assert veredito_do_comparador(-3.0, ">=", 6.0).progresso_pct == 0


def test_piso_com_limiar_nao_positivo_nao_tem_progresso():
    veredito = veredito_do_comparador(5.0, ">=", 0.0)
    assert veredito.conforme is True and veredito.progresso_pct is None


def test_observado_string_do_payload_e_coagido():
    """`protecao_custo_premio` chega como a string "0.005686" — o tipo real do produtor."""
    assert veredito_do_comparador("0.005686", "<=", Decimal("0.01")).conforme is True


@pytest.mark.parametrize("observado", [float("nan"), float("inf"), "N/D", "", None, True, [1.0]])
def test_lado_nao_numerico_ou_nao_finito_nao_julga(observado):
    """NaN fabricaria "violado" — o comparador some em vez de julgar."""
    assert veredito_do_comparador(observado, "<=", 20.0) is None


def test_operador_fora_do_vocabulario_nao_julga():
    assert veredito_do_comparador(5.0, "~=", 20.0) is None
