"""Guards de campo vazio nas narrativas E5.N (Onda R3.2 — PD-01/PD-02/PD-06).

Campo biográfico/estrutural ausente omite a cláusula inteira, sem buracos de
template ("Formado em .", "residência na ", " como contador", "0 viagens/ano
entre R$ 0,00 e R$ 0,00"). Fixtures reusadas do golden decomposition test.
"""

from __future__ import annotations

from datetime import date

from pipeline.domain.services.narrativas import (
    NarrativasContext,
    PerfilFamiliaNarrator,
    SummariesNarrator,
)
from tests.test_e5n_builder_decomposition import _FAMILY_BASE, _build_metrics

_TODAY = date(2026, 4, 20)


def test_perfil_familia_left_sem_buracos_de_fragmento():
    """PD-01: fragmentos do bloco `left` guardados (sem 'Formado em .', 'é  desde')."""
    fam = {
        "titular": "alex",
        "membros": {
            "alex": {"nome_curto": "Alex", "data_nascimento": "1985-03-10"},
            "bia": {"papel": "conjuge", "nome_curto": "Bia", "data_nascimento": "1987-07-22"},
        },
    }
    m = {**_build_metrics(), "salario_conjuge": 0}
    left = PerfilFamiliaNarrator(NarrativasContext.from_family_config(fam)).narrate(
        m, fam, today=_TODAY
    )["left"]
    for hole in ("Formado em .", "Opera como .", "é  desde", "Especialista em ,", "mestre em ."):
        assert hole not in left
    assert "salário-base de R$ 0,00" not in left


def test_summaries_s4_omite_endereco_vazio():
    """PD-02: s4 sem rua → 'residência (' e não 'residência na ('."""
    fam = {**_FAMILY_BASE, "endereco": {}}
    s = SummariesNarrator(NarrativasContext.from_family_config(fam)).narrate(
        _build_metrics(), fam, [], []
    )
    assert "residência na " not in s["s4"] and "residência (" in s["s4"]


def test_summaries_s8_omite_contador_e_holding_vazios():
    """PD-02: s8 sem contador/holding → sem ' como contador' nem 'pendente para .'."""
    m = {**_build_metrics(), "contador_nome": "", "holding_prazo": ""}
    s = SummariesNarrator(NarrativasContext.from_family_config(_FAMILY_BASE)).narrate(
        m, _FAMILY_BASE, [], []
    )
    assert " como contador" not in s["s8"]
    assert "pendente para ." not in s["s8"] and "pendente para 0" not in s["s8"]


def test_summaries_s5_viagens_zero_usa_empty_state():
    """PD-06: 0 viagens / faixa R$ 0–0 → empty-state, não '0 viagens/ano'."""
    m = {**_build_metrics(), "viagens_anuais_estimadas": 0, "custo_viagem_minimo": 0}
    m["custo_viagem_maximo"] = 0
    s = SummariesNarrator(NarrativasContext.from_family_config(_FAMILY_BASE)).narrate(
        m, _FAMILY_BASE, [], []
    )
    assert "0 viagens/ano" not in s["s5"] and "entre R$ 0,00 e R$ 0,00" not in s["s5"]
    assert "não identificado automaticamente" in s["s5"]
