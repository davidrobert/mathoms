"""A40.l80 PR3b ([[ADR-412]] §D7): os produtores publicam o extremo conservador.

A MEDIDA nunca vira `None` — `S7IndependenciaSection.tsx:95` faz `?? 0` e
renderizaria "0,0%", afirmação falsa pior que o número contaminado. O que se
suprime é a PRESCRIÇÃO DIMENSIONADA, e o rótulo qualitativo sobrevive.
"""

from __future__ import annotations

import pytest

from pipeline.domain.services.bases_financeiras import BaseFinanceira
from pipeline.domain.services.carteira_por_papel import build_carteira_por_papel
from pipeline.domain.services.patrimonio_types import MemberIdentity
from pipeline.domain.services.reserva_emergencia_calculator import (
    EmergencyReserveCalculator,
    ReservaEmergenciaConfig,
)

_IDENT = MemberIdentity("david", "mariana", "D", "M")


def _liquido(membro: str, quanto: float) -> dict:
    return {
        "membro": membro,
        "descricao": "CDB LIQUIDEZ DIARIA",
        "tipo": "renda fixa",
        "valor_atual": quanto,
    }


def _patrimonio(titular: float, sem_dono: float, acima_do_piso: bool) -> dict:
    return {
        "investimentos_titular": titular,
        "investimentos_conjuge": 0,
        "investimentos_nao_atribuidos": sem_dono,
        "atribuicao_investimentos": {
            "pct_carteira_financeira": 70.0,
            "motivo": "acima do piso" if acima_do_piso else None,
        },
    }


def _reserva(*, titular: float, sem_dono: float, acima_do_piso: bool = True) -> dict:
    carteira = build_carteira_por_papel(
        {
            "dados": [_liquido("david", titular), _liquido("", sem_dono)],
            "total_por_membro": {"david": titular, "": sem_dono},
        },
        titular_key="david",
        conjuge_key="mariana",
    )
    calc = EmergencyReserveCalculator(ReservaEmergenciaConfig(members=_IDENT))
    return calc.calculate(
        fluxo={"despesa_mensal_media": 10_000},
        patrimonio=_patrimonio(titular, sem_dono, acima_do_piso),
        carteira=carteira,
    )


# -- o intervalo: medida e piso, lado a lado --------------------------------


def test_reserva_publica_medida_e_piso():
    r = _reserva(titular=300_000, sem_dono=700_000)

    assert r["cobertura_meses"] == pytest.approx(100.0)
    assert r["piso_cobertura_meses"] == pytest.approx(30.0)
    assert r["base_do_piso"] == BaseFinanceira.carteira_com_titular_identificado.value


# Mata: derivar o piso de um recomputo do filtro de liquidez. O balde sem dono já
# está DENTRO de `total_liquida` — o piso é subtração, e recomputar abriria espaço
# para os dois lados divergirem.
def test_piso_e_a_medida_menos_o_balde_sem_dono():
    r = _reserva(titular=300_000, sem_dono=700_000)
    sem_dono_meses = r["composicao_liquida"]["investimentos_nao_atribuidos"] / 10_000

    assert r["cobertura_meses"] - r["piso_cobertura_meses"] == pytest.approx(sem_dono_meses)


# -- morre a prescrição, sobrevive a descrição ------------------------------


# Mata: suprimir `avaliacao_liquidity`. Medido: sem ela `HeroKpiGrid.reservaQuality`
# cai num `reservaLabel()` local e RE-DERIVA "excelente", e `_liquidez_excessiva`
# vira falso, desarmando `neutralize_autocontradicao` no parecer.
def test_o_rotulo_sobrevive_a_supressao_da_prescricao():
    r = _reserva(titular=300_000, sem_dono=700_000)

    assert r["prescricao_realocacao_suprimida"] is True
    assert r["avaliacao_liquidity"], "o rótulo NÃO pode sumir junto com a prescrição"
    assert r["cobertura_meses"] is not None, "a medida NÃO pode virar None"


def test_sem_fatia_orfa_nada_e_suprimido():
    r = _reserva(titular=1_000_000, sem_dono=0.0, acima_do_piso=False)

    assert r["prescricao_realocacao_suprimida"] is False
    assert r["motivo_supressao"] is None
    assert r["piso_cobertura_meses"] == pytest.approx(r["cobertura_meses"])


# -- os campos que a §Emenda E3 lista como ÍNTEGROS --------------------------


def test_campos_que_dependem_so_do_denominador_ficam_intactos():
    """Suprimi-los junto seria supressão por atacado ([[ADR-412]] §Emenda E3)."""
    r = _reserva(titular=300_000, sem_dono=700_000)

    for campo in ("custo_essencial_mensal", "meses_alvo", "alvo_brl", "nivel_6_meses"):
        assert r.get(campo) is not None, f"{campo} não depende do numerador contaminado"
