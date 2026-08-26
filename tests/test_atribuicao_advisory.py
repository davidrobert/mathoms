"""A40.l80 PR3a ([[ADR-412]] §D5 · §Emenda E1): o eixo de atribuição diagnostica
sem reter.

A razão nasce ADVISORY porque no E5 `valid = not reasons` e, com `paused_for_review`,
`pipeline_task` retorna ANTES do post-processing: o run não cria row em `reports`
e não roda narrativas, cross-validation nem parecer. Reter tornaria a própria
decisão da ADR inalcançável no run que a motivou.
"""

from __future__ import annotations

import pytest

from pipeline.domain.review_reason import ReviewReasonCode
from pipeline.domain.services.atribuicao_review_reasons import (
    PISO_AGREGADO_PCT,
    atribuicao_investimentos,
    review_reasons_da_atribuicao,
)
from scripts.analyze_finances import _e5_advisory_reasons, _e5_validation_block

_KW = {"stage": "analyze_finances", "artifact_key": "analise_financeira"}


def _patrimonio(orfa: float, cheia: float = 1000.0) -> dict:
    return {
        "investimentos_nao_atribuidos": orfa,
        "atribuicao_investimentos": atribuicao_investimentos(
            orfa=orfa, cheia=cheia, identificada=cheia - orfa
        ),
    }


# -- o piso, nos três degraus da [[ADR-406]] §D1 herdada ---------------------


@pytest.mark.parametrize(
    "orfa,esperado_status,tem_motivo",
    [(0.0, "apurado", False), (5.0, "parcial", False), (480.0, "parcial", True)],
)
def test_piso_decide_entre_silencio_e_nomear(orfa, esperado_status, tem_motivo):
    bloco = atribuicao_investimentos(orfa=orfa, cheia=1000.0, identificada=1000.0 - orfa)
    assert bloco["status"] == esperado_status
    assert bool(bloco["motivo"]) is tem_motivo
    assert bloco["piso_pct"] == PISO_AGREGADO_PCT


def test_status_indeterminado_quando_nada_foi_atribuido():
    """Mata: publicar `apurado` sobre base vazia — afirmação sobre o que não se mediu."""
    assert atribuicao_investimentos(orfa=0.0, cheia=0.0, identificada=0.0)["status"] == (
        "indeterminado"
    )
    assert atribuicao_investimentos(orfa=100.0, cheia=100.0, identificada=0.0)["status"] == (
        "indeterminado"
    )


# -- ADVISORY: diagnostica, não retém ---------------------------------------


def test_razao_dispara_acima_do_piso():
    reasons = review_reasons_da_atribuicao(_patrimonio(480.0), **_KW)
    assert len(reasons) == 1
    assert reasons[0]["code"] == ReviewReasonCode.domain_investimento_sem_titularidade.value


def test_razao_nao_dispara_abaixo_do_piso():
    assert review_reasons_da_atribuicao(_patrimonio(5.0), **_KW) == []


# Mata: emitir a razão dentro de `validation.review_reasons`. Lá ela entraria em
# `valid = not reasons`, o run pausaria e NÃO produziria relatório algum.
def test_razao_advisory_nao_retem_o_run():
    patrimonio = _patrimonio(480.0)

    advisory = _e5_advisory_reasons(patrimonio)
    bloco = _e5_validation_block(patrimonio, None)

    assert len(advisory) == 1, "a razão advisory tem de existir"
    assert bloco["valid"] is True, "advisory NÃO pode reter o run"
    assert bloco["review_reasons"] == [], "advisory não entra em validation"


def test_harvest_enxerga_a_razao_advisory():
    """Sem isto a razão seria inerte: emitida, nunca persistida."""
    from pipeline.domain.review_reason_harvest import harvest_review_reasons

    patrimonio = _patrimonio(480.0)
    detail = {
        "validation": _e5_validation_block(patrimonio, None),
        "review_reasons": _e5_advisory_reasons(patrimonio),
    }
    colhidas = harvest_review_reasons(detail)

    codes = {r["code"] for r in colhidas}
    assert ReviewReasonCode.domain_investimento_sem_titularidade.value in codes


def test_code_e_proprio_e_nao_o_de_membro_nao_apurado():
    """`nao_apurado` é ausência de medição de pessoa que existe (fica FORA da
    base); `sem_titularidade` é presença de medição sem etiqueta (fica DENTRO).
    A remediação difere: um pede documento, o outro reconciliação."""
    reasons = review_reasons_da_atribuicao(_patrimonio(480.0), **_KW)
    assert reasons[0]["code"] != ReviewReasonCode.domain_membro_nao_apurado.value
