"""Narrador do card Atual vs Alvo sob supressão ([[ADR-394]] §Emenda · [[ADR-400]]).

A frase é a mesma do card React: este teste e
`frontend/tests/components/report/alocacaoSupressao.test.ts` leem
`tests/fixtures/narrativas/alocacao_supressao_frases.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipeline.domain.services.narrativas.alocacao_narrator import narrate_alocacao_atual_vs_alvo
from pipeline.domain.services.narrativas.alocacao_supressao import frase_da_supressao

_FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures/narrativas/alocacao_supressao_frases.json"
)
_FRASES: list[dict[str, str]] = json.loads(_FIXTURE.read_text(encoding="utf-8"))["rodape"]

_DERIVED: dict[str, Any] = {
    "comparaveis": [
        {"classe": "renda_fixa", "atual_pct": 50.0, "alvo_pct": 60.0, "desvio_pp": -10.0},
        {"classe": "acoes_br", "atual_pct": 40.0, "alvo_pct": 30.0, "desvio_pp": 10.0},
        {"classe": "fora_alvo", "atual_pct": 10.0, "alvo_pct": 10.0, "desvio_pp": 0.0},
    ],
    "desvio_max_pct": 10.0,
    "next_aporte_classe": "renda_fixa",
    "carteira_liquida_brl": 100_000.0,
    "caixa": {"valor_brl": 0.0},
    "imoveis_fisicos_brl": 0.0,
    "has_alvo": True,
}


def _conclusion(**derived: Any) -> str:
    metrics = {"aloc_derived": _DERIVED | derived, "aloc_rebalanceamento": "por_aporte"}
    return narrate_alocacao_atual_vs_alvo(metrics)["conclusion"]


def _suprimida(motivo: str, **derived: Any) -> str:
    sem_prescricao = {"next_aporte_classe": None, "desvio_max_pct": None}
    return _conclusion(**(sem_prescricao | derived), motivo_supressao=motivo)


@pytest.mark.parametrize("caso", _FRASES, ids=lambda caso: caso["motivo"])
def test_frase_da_supressao_e_a_mesma_do_card(caso):
    assert frase_da_supressao(caso["motivo"]) == caso["frase"]


@pytest.mark.parametrize("caso", _FRASES, ids=lambda caso: caso["motivo"])
def test_conclusao_suprimida_fecha_na_frase_e_mantem_a_descricao(caso):
    conclusion = _suprimida(caso["motivo"])
    assert conclusion.startswith("Renda Fixa 50%→60%, Ações BR 40%→30%")
    assert conclusion.endswith(" " + caso["frase"])


@pytest.mark.parametrize(
    "motivo",
    ["cobertura_incompleta: conjuge", "balde_negativo: veiculos", "valor_nao_apurado: 2 item(ns)"],
)
def test_supressao_nao_atribui_a_classe_o_que_e_de_cobertura(motivo):
    """A causa publicada é a do produtor; antes, toda supressão virava "sem classe"."""
    assert "sem classe" not in _suprimida(motivo)


def test_supressao_parcial_nao_prescreve_nem_julga_o_desvio():
    """Com 2–10% sem classe o `desvio_max_pct` fica no payload ([[ADR-400]]), não na prosa."""
    conclusion = _suprimida("nao_classificado: 5.1% da carteira", desvio_max_pct=10.0)
    for prescricao in ("Maior desvio", "Próximo aporte:", "aderente", "Rebalanceamento"):
        assert prescricao not in conclusion, prescricao


def test_sem_supressao_mantem_a_prescricao():
    assert _conclusion().endswith(
        "Maior desvio: 10 pp. Próximo aporte: Renda Fixa. Rebalanceamento por aporte."
    )
    assert _conclusion(motivo_supressao=None).endswith("Rebalanceamento por aporte.")
