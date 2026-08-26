"""A40.l80 PR3b C3 ([[ADR-412]] §D7 · §Emenda E4): o predicado único de supressão.

Ele existe para que nenhum produtor resolva supressão por dentro — que é
literalmente como nasceu o defeito desta lane (`_positions_for_member` resolvendo
titularidade dentro do consumidor da reserva).
"""

from __future__ import annotations

import pytest

from pipeline.domain.services.bases_financeiras import BaseFinanceira
from pipeline.domain.services.supressao_por_atribuicao import (
    DEGRAU_DEFICIT_MESES,
    DEGRAU_EXCEDENTE_MESES,
    DEGRAU_PRAZO_ANOS,
    SupressaoPorAtribuicao,
)


def _sup(*, acima: bool = True, pct: float = 48.1) -> SupressaoPorAtribuicao:
    return SupressaoPorAtribuicao(
        acima_do_piso=acima,
        pct_sem_titular=pct,
        base_medida=BaseFinanceira.carteira_financeira_familia,
        base_piso=BaseFinanceira.carteira_com_titular_identificado,
    )


# -- o call-site que `publicavel_sozinha` não tinha --------------------------


# Mata: inverter o `not in` de BASES_SO_COMO_EXTREMO_DE_INTERVALO. Antes deste
# commit o único "uso" do predicado era um teste-espelho que reafirmava a
# constante — faceta inerte, não gate.
def test_base_da_medida_tem_de_ser_publicavel_sozinha():
    with pytest.raises(ValueError, match="publicável sozinha"):
        SupressaoPorAtribuicao(
            acima_do_piso=True,
            pct_sem_titular=1.0,
            base_medida=BaseFinanceira.carteira_com_titular_identificado,
            base_piso=BaseFinanceira.carteira_com_titular_identificado,
        )


def test_base_do_piso_tem_de_ser_extremo_de_intervalo():
    with pytest.raises(ValueError, match="extremo de intervalo"):
        SupressaoPorAtribuicao(
            acima_do_piso=True,
            pct_sem_titular=1.0,
            base_medida=BaseFinanceira.carteira_financeira_familia,
            base_piso=BaseFinanceira.carteira_financeira_familia,
        )


# -- o kill-switch que NÃO se herda ------------------------------------------


# Mata: reusar `motivo_supressao_por_cobertura`, que abre com
# `if not cobertura_enforcement_ligado(): return None`. Prescrição errada não é
# ruído — é conselho, e não pode ser desligável por env var ([[ADR-412]] §D8).
def test_supressao_nao_e_desligavel_por_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MATHOMS_E5_COBERTURA_MEMBRO", "0")
    motivo = _sup().de_reserva(medida_meses=43.9, piso_meses=25.4, meses_alvo=18.0)
    assert motivo is not None


# -- a régua: meses da quantidade acionável, não razão -----------------------


def test_abaixo_do_piso_nada_e_suprimido():
    assert _sup(acima=False).de_reserva(medida_meses=43.9, piso_meses=25.4, meses_alvo=18.0) is None


# Mata: trocar o degrau por 0.0 — gate que sempre dispara é gate morto.
def test_spread_menor_que_o_degrau_nao_suprime():
    medida, piso = 30.0, 30.0 + DEGRAU_EXCEDENTE_MESES - 0.1
    assert _sup().de_reserva(medida_meses=piso, piso_meses=medida, meses_alvo=18.0) is None
    assert DEGRAU_EXCEDENTE_MESES > 0, "degrau zero faria o gate disparar sempre"


def test_spread_no_degrau_suprime():
    piso = 30.0
    medida = piso + DEGRAU_EXCEDENTE_MESES
    assert _sup().de_reserva(medida_meses=medida, piso_meses=piso, meses_alvo=18.0) is not None


# Mata: usar o degrau de excedente quando a família está ABAIXO do alvo. Ali cada
# mês é aporte que ela tem de fazer, e o erro para menos é o caro.
def test_abaixo_do_alvo_usa_o_degrau_de_deficit():
    piso, alvo = 3.0, 18.0
    medida = piso + DEGRAU_DEFICIT_MESES
    assert medida - piso < DEGRAU_EXCEDENTE_MESES
    assert _sup().de_reserva(medida_meses=medida, piso_meses=piso, meses_alvo=alvo) is not None


# Mata: ancorar a materialidade em flip de rótulo. `"Excessiva"` é faixa ABERTA no
# topo, então nenhum erro, de qualquer tamanho, a faz flipar — gate ancorado em
# flip é cego por construção ali. Quando o intervalo CRUZA o alvo, porém, os dois
# extremos discordam sobre estar acima ou abaixo, e nenhum degrau salva.
def test_intervalo_que_cruza_o_alvo_suprime_sem_depender_do_degrau():
    alvo = 18.0
    motivo = _sup().de_reserva(medida_meses=alvo + 0.1, piso_meses=alvo - 0.1, meses_alvo=alvo)
    assert motivo is not None
    assert "cruza o alvo" in motivo


def test_prazo_usa_o_extremo_mais_longo():
    assert _sup().de_prazo(medida_anos=9.0, teto_anos=9.0 + DEGRAU_PRAZO_ANOS) is not None
    assert _sup().de_prazo(medida_anos=9.0, teto_anos=9.0) is None
    assert _sup().de_prazo(medida_anos=None, teto_anos=None) is None


def test_autonomia_usa_o_degrau_de_deficit():
    assert _sup().de_autonomia(medida_meses=18.1, piso_meses=9.2) is not None
    assert _sup().de_autonomia(medida_meses=9.2, piso_meses=9.2) is None


# -- o motivo carrega o número, e o número é razão, nunca BRL ----------------


def test_motivo_nomeia_a_causa_e_a_grandeza():
    motivo = _sup(pct=48.1).de_reserva(medida_meses=43.9, piso_meses=25.4, meses_alvo=18.0)
    assert "atribuicao_incompleta" in motivo
    assert "48.1%" in motivo
    assert "excedente da reserva" in motivo


# -- lê o eixo do PR3a, não recomputa ----------------------------------------


def test_do_patrimonio_le_o_eixo_publicado():
    """Mata: recomputar a atribuição aqui — seria o quinto resolver da lane."""
    sup = SupressaoPorAtribuicao.do_patrimonio(
        {"atribuicao_investimentos": {"pct_carteira_financeira": 48.13, "motivo": "acima do piso"}}
    )
    assert sup.acima_do_piso is True
    assert sup.pct_sem_titular == pytest.approx(48.13)


def test_do_patrimonio_sem_o_bloco_nao_suprime():
    """Payload legado (pré-PR3a) não pode suprimir por ausência de campo."""
    assert SupressaoPorAtribuicao.do_patrimonio({}).acima_do_piso is False
