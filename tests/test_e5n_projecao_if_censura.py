"""Copy da projeção de IF sob censura de percentil (ADR-361).
Separado de ``test_e5n_narrativas_coerentes`` por responsabilidade: são os quatro
estados publicáveis do cone, e o de origem passou do teto de 500 linhas.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.test_e5n_narrativas_coerentes import _charts, _metrics_base

# Prazo declarado sintético, comum aos estados abaixo — a oração do prazo é
# ortogonal à censura do cone, então repeti-la em cada fixture só empurraria os
# testes para além do teto de 20 linhas sem cobrir nada a mais.
_PRAZO = {
    "mc_prob_if_ate_prazo_declarado": 0.31,
    "mc_prazo_declarado_anos": 15,
    "mc_ano_alvo_declarado": 2041,
    "mc_declarado_em": "2026-03-01",
}


def test_projecao_mediana_censurada_nao_cai_no_deterministico():
    """ADR-361: `p50=None` não pode virar "a trajetória aponta a meta para X"."""
    # Sem o ramo de censura, a frase mais otimista do relatório sairia justamente
    # no plano em que a mediana não atinge a meta no horizonte.
    m = _metrics_base() | {
        "mc_ano_if_cenario_central": None,
        "mc_ano_if_cenario_central_censurado": True,
        "mc_ano_if_cenario_adverso_censurado": True,
        "mc_prob_if_ate_horizonte_simulado": 0.436,
        "mc_horizonte_simulado_anos": 40,
        **_PRAZO,
    }
    conclusion = _charts(m)["projecao_3cenarios"]["conclusion"]
    assert "não é atingida dentro dos 40 anos" in conclusion
    assert "trajetória projetada aponta a meta para" not in conclusion
    assert "2038" not in conclusion, "ano determinístico vazou na mediana censurada"
    assert "será atingida" not in conclusion
    assert "aporte mensal" in conclusion


def test_projecao_cenario_adverso_censurado_declara_horizonte():
    """Sucesso entre 55% e 95%: central existe, adverso fica fora do horizonte."""
    m = _metrics_base() | {
        "mc_ano_if_cenario_favoravel": 2044,
        "mc_ano_if_cenario_central": 2053,
        "mc_ano_if_cenario_adverso": None,
        "mc_ano_if_cenario_adverso_censurado": True,
        "mc_prob_if_ate_horizonte_simulado": 0.8821,
        **(_PRAZO | {"mc_prob_if_ate_prazo_declarado": 0.41}),
        "mc_horizonte_simulado_anos": 40,
    }
    conclusion = _charts(m)["projecao_3cenarios"]["conclusion"]
    assert "2053" in conclusion
    assert "além dos 40 anos projetados" in conclusion
    assert "no adverso" not in conclusion, "não pode datar um adverso censurado"


def test_projecao_faixa_completa_publica_os_dois_extremos():
    """Plano folgado: a faixa sai como faixa, não como ponto."""
    m = _metrics_base() | {
        "mc_ano_if_cenario_favoravel": 2039,
        "mc_ano_if_cenario_central": 2046,
        "mc_ano_if_cenario_adverso": 2058,
        "mc_prob_if_ate_horizonte_simulado": 0.99,
        **(_PRAZO | {"mc_prob_if_ate_prazo_declarado": 0.62}),
        "mc_horizonte_simulado_anos": 40,
    }
    conclusion = _charts(m)["projecao_3cenarios"]["conclusion"]
    assert "entre 2039 no cenário favorável e 2058 no adverso" in conclusion
    assert "além dos 40 anos" not in conclusion


def test_projecao_deterministica_sem_prazo_emite_ausencia():
    """#1158 aposentou a sentinela 999: sem prazo, `if_ano` é None."""
    # A ADR-361 guardava `if_prazo_anos >= 999`; o contrato agora é ausência.
    m = _metrics_base() | {"if_prazo_anos": None, "if_ano": None, "idade_titular_if": None}
    conclusion = _charts(m)["projecao_3cenarios"]["conclusion"]
    assert "3025" not in conclusion
    assert "não projeta um ano para a meta" in conclusion


# ----------------------------------------------------------------------
# FIN-08 — projeção IF probabilística (if_monte_carlo)
# ----------------------------------------------------------------------


def test_projecao_probabilistica_com_monte_carlo():
    m = _metrics_base() | {
        "mc_ano_if_cenario_central": 2039,
        **(_PRAZO | {"mc_prob_if_ate_prazo_declarado": 0.41}),
    }
    conclusion = _charts(m)["projecao_3cenarios"]["conclusion"]
    assert "2039" in conclusion
    assert "41%" in conclusion
    # ADR-369 D2: a proveniência do alvo é obrigatória — sem "você declarou" e a
    # data da declaração, o leitor lê a data como nossa.
    assert "15 anos que você declarou" in conclusion
    assert "março de 2026" in conclusion
    assert "2041" in conclusion
    assert "será atingida" not in conclusion


def test_projecao_fallback_deterministico_sem_promessa():
    conclusion = _charts(_metrics_base())["projecao_3cenarios"]["conclusion"]
    assert "2038" in conclusion
    assert "será atingida" not in conclusion
    assert "será" not in conclusion


@pytest.mark.parametrize(
    ("prob", "esperado"),
    [(0.004, "<1%"), (0.995, ">99%"), (0.5, "50%")],
)
def test_projecao_probabilidade_guards(prob: float, esperado: str):
    m = _metrics_base() | {
        "mc_ano_if_cenario_central": 2039,
        "mc_prob_if_ate_prazo_declarado": prob,
        "mc_prazo_declarado_anos": 15,
        "mc_ano_alvo_declarado": 2041,
        "mc_declarado_em": "2026-03-01",
    }
    conclusion = _charts(m)["projecao_3cenarios"]["conclusion"]
    assert esperado in conclusion
