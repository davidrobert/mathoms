"""Card "Sem renda do cônjuge" sem aporte declarado — zero no lugar de ausente (COPY_GUIDELINES §4.3)."""

from __future__ import annotations

from typing import Any

import pytest

from pipeline.domain.services.narrativas import ChartsNarrator, NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import (
    CENARIO_CONJUGE_META_ATINGIDA,
    CENARIO_CONJUGE_SEM_APORTE,
)
from tests.test_e5n_builder_decomposition import _FAMILY_BASE, _build_metrics


def _narra_cenario(**overrides: Any) -> dict[str, str]:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    metrics = {**_build_metrics(), **overrides}
    return ChartsNarrator(ctx).narrate(metrics, _FAMILY_BASE, [], [])["cenarios_conjuge"]


# `None` é a forma que o E5 publica; `0` é a do artefato E5 persistido antes dela.
# Zero nunca é declaração de aporte (ADR-373), então as duas são a mesma ausência.
@pytest.mark.parametrize("aporte", [None, 0])
def test_sem_aporte_declarado_a_conclusao_nao_afirma_zero(aporte):
    cenario = _narra_cenario(cm_aportes=[aporte], cm_prazos=[None], cm_anos_if=[None])

    assert "R$ 0" not in cenario["conclusion"]
    assert "N/D" not in cenario["conclusion"]
    assert "aporte-base" not in cenario["conclusion"]
    # ADR-373 D2: a redação nomeava a nossa incapacidade, não o insumo que falta.
    assert "não projetável" not in cenario["conclusion"]
    # Mesma frase do resumo do E5: um produtor só para as três superfícies.
    assert cenario["conclusion"] == CENARIO_CONJUGE_SEM_APORTE


def test_sem_aporte_com_meta_atingida_afirma_so_o_fato_de_hoje():
    cenario = _narra_cenario(cm_aportes=[None], cm_prazos=[0.0], cm_anos_if=[2026])

    assert cenario["conclusion"] == CENARIO_CONJUGE_META_ATINGIDA


def test_com_aporte_declarado_a_conclusao_segue_quantificada():
    cenario = _narra_cenario(cm_aportes=[10_000], cm_prazos=[18], cm_anos_if=[2044])

    assert "R$ 10k/mês" in cenario["conclusion"]
    assert "IF em 18 anos (2044)" in cenario["conclusion"]
