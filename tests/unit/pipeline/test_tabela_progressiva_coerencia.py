"""Invariantes da tabela progressiva (A40.l56 · ADR-389 D3) — cada teste mata um vintage."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.tabela_progressiva_coerencia import (
    divergencia_x12,
    verificar_congruencia,
    verificar_continuidade,
    verificar_monotonicidade,
    verificar_primeira_fronteira,
)
from pipeline.domain.types.config import IRPFBracket


def _faixas(linhas) -> tuple[IRPFBracket, ...]:
    return tuple(
        IRPFBracket(upper_brl_cents=u, aliquota_pct=Decimal(a), deducao_brl_cents=d)
        for a, u, d in linhas
    )


# Tabela ANUAL AC2026 (ADR-389 D2) — a que a migration vai gravar.
ANUAL_2026 = _faixas(
    [
        ("0.0", 2914560, 0),
        ("7.5", 3391980, 218592),
        ("15.0", 4501260, 472991),
        ("22.5", 5597616, 810585),
        ("27.5", None, 1090466),
    ]
)

# Tabela MENSAL viva em produção hoje (`cascata_calculator.IRRF_TABELA_MENSAL`,
# MP 1.294/2025), em cents.
MENSAL_2026 = _faixas(
    [
        ("0.0", 242880, 0),
        ("7.5", 282665, 18216),
        ("15.0", 375105, 39416),
        ("22.5", 466468, 67549),
        ("27.5", None, 90873),
    ]
)

# Tabela ANUAL AC2024 — o ano de transição, cujo teto isento é mistura ponderada
# por mês (2.112,00×1 + 2.259,20×11), não ×12 de nada.
ANUAL_2024 = _faixas(
    [
        ("0.0", 2696320, 0),
        ("7.5", 3391980, 202224),
        ("15.0", 4501260, 456623),
        ("22.5", 5597616, 794217),
        ("27.5", None, 1074098),
    ]
)


@pytest.mark.parametrize(
    "tabela", [ANUAL_2026, MENSAL_2026, ANUAL_2024], ids=["anual26", "mensal26", "anual24"]
)
def test_tabelas_reais_sao_continuas(tabela):
    assert verificar_continuidade(tabela) == ()


@pytest.mark.parametrize(
    "tabela", [ANUAL_2026, MENSAL_2026, ANUAL_2024], ids=["anual26", "mensal26", "anual24"]
)
def test_tabelas_reais_fecham_a_primeira_fronteira_exatamente(tabela):
    assert verificar_primeira_fronteira(tabela) == ()


def test_o_defeito_original_e_pego_pela_primeira_fronteira():
    """O seed misturava teto anual de AC2024 com parcela mensal ×12 — R$ 11,04."""
    misturada = _faixas(
        [
            ("0.0", 2696320, 0),
            ("7.5", 3391980, 203328),  # 16944 (mensal) × 12
            ("15.0", 4501260, 457728),
            ("22.5", 5597616, 795324),
            ("27.5", None, 1075200),
        ]
    )
    violacoes = verificar_primeira_fronteira(misturada)
    assert violacoes, "o invariante exato tem que pegar o vintage misturado"
    assert "1104" in violacoes[0].detalhe.replace(".", "").replace(",", "")


def test_um_centavo_de_erro_em_parcela_derruba_a_continuidade():
    """Prova que a tolerância de R$ 0,01 não é frouxa demais para o ruído real."""
    linhas = [
        ("0.0", 2914560, 0),
        ("7.5", 3391980, 218592),
        ("15.0", 4501260, 472991 + 2),
        ("22.5", 5597616, 810585),
        ("27.5", None, 1090466),
    ]
    assert verificar_continuidade(_faixas(linhas))


def test_congruencia_pega_tabela_com_faixa_faltando():
    truncada = ANUAL_2026[:-1]
    assert verificar_congruencia(MENSAL_2026, truncada)


def test_congruencia_aceita_o_par_real():
    assert verificar_congruencia(MENSAL_2026, ANUAL_2026) == ()


def test_monotonicidade_pega_teto_que_nao_cresce():
    quebrada = _faixas([("0.0", 2914560, 0), ("7.5", 2914560, 218592), ("27.5", None, 1090466)])
    assert verificar_monotonicidade(quebrada)


def test_ano_limpo_nao_exige_motivo_de_divergencia():
    """AC2026 não teve transição: o desvio ×12 é arredondamento (≤ R$ 0,10)."""
    assert divergencia_x12(MENSAL_2026, ANUAL_2026) == ()


def test_ano_de_transicao_exige_motivo_declarado():
    """AC2024 é mistura ponderada — a faixa isenta diverge R$ 147,20 do ×12."""
    assert 0 in divergencia_x12(MENSAL_2026, ANUAL_2024)
