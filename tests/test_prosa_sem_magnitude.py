"""A40.l80 PR3b ([[ADR-412]] §Emenda E3): a prosa determinística morre no produtor.

Regra pós-LLM **não alcança** texto que já saiu pronto daqui — foi exatamente
assim que o "verde" da banda cambial vazou para o parecer apesar de o campo
`tier` dizer `indeterminado`. Por isso a supressão acontece no produtor.
"""

from __future__ import annotations

import pytest

from pipeline.domain.services.pontos_fortes_analyzer import PontosFortesAnalyzer
from pipeline.domain.services.pontos_urgentes_analyzer import _impacto_reserva

_MOTIVO = "atribuicao_incompleta: 48.1% da carteira financeira sem titular identificado"


def _reserva(*, cobertura: float, piso: float, suprimida: bool) -> dict:
    return {
        "cobertura_meses": cobertura,
        "piso_cobertura_meses": piso,
        "meses_alvo": 18.0,
        "avaliacao_liquidity": "Excessiva",
        "motivo_supressao": _MOTIVO if suprimida else None,
    }


def _descricoes(reserva: dict) -> str:
    itens = PontosFortesAnalyzer().analyze(
        score={}, reserva=reserva, ratios={}, goals={}, patrimonio={}, fluxo={}
    )
    return " ".join(i.descricao for i in itens)


# -- a magnitude e a prescrição morrem; o item e o alvo sobrevivem -----------


def test_reserva_robusta_perde_a_magnitude_e_a_prescricao():
    texto = _descricoes(_reserva(cobertura=43.9, piso=25.4, suprimida=True))

    assert "44 meses" not in texto, "a magnitude contaminada não pode ser impressa"
    assert "realocado" not in texto, "a prescrição dimensionada não pode sobreviver"
    assert "18 meses" in texto, "`meses_alvo` não depende do numerador — tem de ficar"


def test_sem_supressao_a_prescricao_continua():
    """Mata: suprimir sempre. Sem fatia órfã o conselho é legítimo."""
    texto = _descricoes(_reserva(cobertura=43.9, piso=43.9, suprimida=False))

    assert "44 meses" in texto
    assert "realocado" in texto


# Mata: avaliar "≥2× o alvo" sobre a cobertura MEDIDA. Com fatia sem dono ela
# infla, e o item dispararia sobre número que a atribuição não sustenta.
def test_o_segundo_braco_avalia_no_extremo_conservador():
    analyzer = PontosFortesAnalyzer()
    reserva = {
        "cobertura_meses": 40.0,  # ≥ 2× o alvo — dispararia pela medida
        "piso_cobertura_meses": 20.0,  # < 2× o alvo — não dispara pelo piso
        "meses_alvo": 18.0,
        "avaliacao_liquidity": "Robusta",
        "motivo_supressao": _MOTIVO,
    }
    titulos = {
        i.titulo
        for i in analyzer.analyze(
            score={}, reserva=reserva, ratios={}, goals={}, patrimonio={}, fluxo={}
        )
    }

    assert "Reserva de Emergência Robusta" not in titulos


# -- a mesma frase vive em DOIS produtores ----------------------------------


@pytest.mark.parametrize("suprimida,tem_magnitude", [(True, False), (False, True)])
def test_impacto_da_reserva_insuficiente(suprimida: bool, tem_magnitude: bool):
    """Mata: consertar só o domain service. `scripts/analyze_finances.py` importa
    ESTA função — os dois produtores mudam juntos ([[ADR-412]] §Emenda E2)."""
    texto = _impacto_reserva(3.0, 6.0, suprimida)

    assert ("3 meses" in texto) is tem_magnitude
    assert "6 meses" in texto or "mínimo de 6" in texto


def test_o_produtor_legado_usa_a_mesma_funcao():
    """Verificação estrutural: a divergência stage↔legado é impossível se há um só texto."""
    import pathlib

    legado = pathlib.Path("scripts/analyze_finances.py").read_text()
    assert "_impacto_reserva(" in legado
    assert 'f"Cobertura atual de {cobertura:.0f} meses' not in legado
