"""ADR-373 — a S1 não afirma que aportes fecham o gap quando não há aporte.

Achado de passagem da A40.l26, e independente do solver: com
`meta_aporte_mensal == 0` a conclusão do `waterfall_if` já saía como *"Gap de
R$ 87,0M será fechado por aportes disciplinados (R$ 0,00/mês = R$ 0,00 em N/D
anos)"* — falsa, na seção 1, antes de qualquer mudança neste PR.
"""

from __future__ import annotations

from pipeline.domain.services.narrativas.charts_narrator import (
    _narrate_waterfall_if_conclusion,
)


def _metrics(**over) -> dict:
    base = {
        "if_gap": 87_000_000.0,
        "meta_aporte_mensal": 0.0,
        "aportes_acum_prazo": 0.0,
        "if_prazo_anos": None,
        "if_retorno_real_pct": 6.0,
    }
    base.update(over)
    return base


def test_sem_aporte_declarado_nao_afirma_que_aportes_fecham_o_gap() -> None:
    """Mutação que mata: voltar à frase única."""
    frase = _narrate_waterfall_if_conclusion(_metrics())

    assert "aportes disciplinados" not in frase
    assert "R$ 0,00/mês" not in frase


def test_sem_aporte_declarado_nomeia_o_insumo_que_falta() -> None:
    frase = _narrate_waterfall_if_conclusion(_metrics())

    assert "ainda não declarou" in frase
    assert "N/D" not in frase  # nem o placeholder de prazo ausente vaza


def test_sem_aporte_declarado_ainda_declara_o_gap_e_a_premissa_de_retorno() -> None:
    """Retirar a afirmação falsa não pode virar linha muda."""
    frase = _narrate_waterfall_if_conclusion(_metrics())

    assert "R$ 87,0M" in frase
    assert "6% a.a." in frase


def test_com_aporte_declarado_a_frase_original_permanece() -> None:
    frase = _narrate_waterfall_if_conclusion(
        _metrics(meta_aporte_mensal=20_000.0, aportes_acum_prazo=3_100_000.0, if_prazo_anos=13.0)
    )

    assert "será fechado por aportes disciplinados" in frase
    assert "em 13 anos" in frase


def test_aporte_declarado_mas_prazo_ausente_tambem_cai_no_ramo_honesto() -> None:
    """`if_prazo_anos is None` com aporte > 0 é o caso de não-convergência."""
    frase = _narrate_waterfall_if_conclusion(_metrics(meta_aporte_mensal=20_000.0))

    assert "aportes disciplinados" not in frase
