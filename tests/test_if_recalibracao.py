"""Ledger de recalibração do MC — o gatilho da nota one-shot (A40.l25 · ADR-360)."""
# O gate audita o LEDGER, não o texto: bump de `_MC_VERSION` sem entrada
# declarada avermelha aqui, que é o que impede a nota de ficar stale no
# próximo deslocamento do bloco de IF.

from __future__ import annotations

import pytest

from pipeline.domain.services.if_monte_carlo import _MC_VERSION
from pipeline.domain.services.if_recalibracao import (
    FACETA_ANO_CONE,
    FACETA_PROBABILIDADE_ALVO,
    majors_declarados,
    mc_major,
    resolve_facetas,
)


def test_versao_corrente_tem_efeito_declarado_no_ledger() -> None:
    major = int(_MC_VERSION.split(".", 1)[0])
    assert major in majors_declarados(), (
        f"`_MC_VERSION` foi bumpada para {_MC_VERSION} sem declarar o efeito em "
        "_EFEITOS_POR_MC_VERSION. Sem a entrada, a nota de recalibração cala "
        "para todo mundo e o cliente vê o número mudar sem aviso."
    )


@pytest.mark.parametrize(
    ("bloco", "esperado"),
    [
        ({"mc_version": "5.0"}, 5),
        ({"mc_version": "3.0"}, 3),
        ({"mc_version": "10.0"}, 10),
        # Bloco LEGÍVEL sem carimbo é evidência de v1 — não é ausência de evidência.
        ({}, 1),
        ({"mc_version": None}, 1),
    ],
)
def test_mc_major(bloco: dict, esperado: int) -> None:
    assert mc_major(bloco) == esperado


def test_rename_only_nao_move_faceta_nenhuma() -> None:
    """3.0 → 4.0 renomeou chaves com valores idênticos (ADR-369 D1): sem nota."""
    assert resolve_facetas(3, 4) == ()


def test_mudanca_de_alvo_move_a_probabilidade_sem_mover_o_ano() -> None:
    assert resolve_facetas(3, 5) == (FACETA_PROBABILIDADE_ALVO,)


def test_workspace_que_pula_versoes_recebe_todas_as_facetas_numa_nota_so() -> None:
    """v1 → 5.0 acumula o ano (2.0/3.0) e a probabilidade (5.0), na ordem da seção."""
    assert resolve_facetas(1, 5) == (FACETA_ANO_CONE, FACETA_PROBABILIDADE_ALVO)


def test_mesma_versao_nos_dois_lados_nao_produz_faceta() -> None:
    assert resolve_facetas(5, 5) == ()


def test_intervalo_e_semiaberto_a_esquerda() -> None:
    """O bump do PRÓPRIO anterior já foi avisado no relatório dele."""
    assert FACETA_ANO_CONE not in resolve_facetas(3, 4)
    assert FACETA_ANO_CONE in resolve_facetas(2, 3)
