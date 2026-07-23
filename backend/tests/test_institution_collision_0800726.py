"""A38.l4 — colisão `0800 726`: SAC Libras do Santander casava o pattern da Caixa."""

from __future__ import annotations

from backend.app.services.classification.institution_classifier import (
    detect_institution_by_content,
)

_CONSOLIDADO_JUN = (
    "EXTRATO CONSOLIDADO INTELIGENTE\n"
    "junho/2026\n"
    "Confira mais detalhes em: https://www.santander.com.br/campanhas/work-cafe\n"
    "Extrato_PF_A4_Inteligente - 27/11/2024\n"
    "às 18h, exceto feriados. todos os dias.\n"
    "0800 726 0322\n"
    "Libras (SAC e Ouvidoria)\n"
)

_CONSOLIDADO_MAI = (
    "EXTRATO CONSOLIDADO INTELIGENTE\n"
    "maio/2026\n"
    "Extrato_PF_A4_Inteligente - 27/11/2024\n"
    "JUROS SALDO UTILIZ ATE LIMITE - 1,00-\n"
)

_CEF_LEGITIMO = (
    "CAIXA ECONÔMICA FEDERAL\n"
    "Extrato por período\n"
    "Alô CAIXA: 0800 726 0101\n"
    "SAC CAIXA: 0800 726 0104\n"
)


def test_sac_libras_santander_nao_vira_caixa() -> None:
    """Regressão do corpus 2026-07-22: consolidado de junho classificava caixa
    conf 1.0 via `0800 726` — e conf 1.0 impede o LLM fallback de corrigir."""
    assert detect_institution_by_content(_CONSOLIDADO_JUN) == "santander"


def test_consolidado_sem_ramal_detecta_santander_pelo_template() -> None:
    assert detect_institution_by_content(_CONSOLIDADO_MAI) == "santander"


def test_cef_legitima_continua_caixa() -> None:
    assert detect_institution_by_content(_CEF_LEGITIMO) == "caixa"


def test_ramal_0800726_generico_sozinho_nao_e_mais_ancora() -> None:
    assert detect_institution_by_content("atendimento: 0800 726 0322") is None
