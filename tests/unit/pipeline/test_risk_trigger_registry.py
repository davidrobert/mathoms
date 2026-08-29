"""Os dois instrumentos do [[ADR-419]] §D4 — um só não pega.

O invariante é **por chave**. A forma existencial (`count(rompidos) > 0 ⟹ len(itens) > 0`)
foi medida no dogfood e **passa com o defeito inteiro presente**, porque o consequente é
satisfeito por `rentabilidade_nao_medida`, que não compara limiar nenhum. O teste
`test_forma_existencial_nao_discrimina` congela essa medição: se alguém trocar o
invariante pela forma antiga, ele mostra por que não serve.
"""

from __future__ import annotations

import pytest

from pipeline.domain.services.pontos_urgentes_analyzer import (
    PontosUrgentesAnalyzer,
    PontosUrgentesConfig,
)
from pipeline.domain.services.risk_trigger_registry import (
    DISPENSADAS,
    build_risk_triggers,
    chaves_sob_o_gate,
)

SCORING = {"thresholds_alertas": {"reserva_minima_meses": 6, "endividamento_maximo_pct": 20}}

# Sem gap de vida e com rentabilidade medida: as regras que NÃO comparam limiar ficam
# caladas, para que o teste meça o gatilho e não o ruído ao lado dele.
_PROTECAO_SEM_GAP = {
    "gap_qualitativo": [{"categoria": "vida", "flag": False, "rationale": "apolice_vida_ativa"}],
    "apolices_vigentes": [{"x": 1}],
}


def _analyze(*, endiv: float, cobertura: float, rentabilidade=7.2):
    analyzer = PontosUrgentesAnalyzer(PontosUrgentesConfig.from_scoring(SCORING))
    return analyzer.analyze(
        {"taxa_endividamento_pct": endiv, "rentabilidade_pct": rentabilidade},
        {"piso_cobertura_meses": cobertura},
        {},
        _PROTECAO_SEM_GAP,
    )


def _observado_conforme(kpi_key: str) -> float:
    return {"reserva_cobertura_meses": 53.3, "taxa_endividamento": 5.0}[kpi_key]


def _observado_rompido(kpi_key: str) -> float:
    return {"reserva_cobertura_meses": 1.0, "taxa_endividamento": 45.0}[kpi_key]


def _kwargs(kpi_key: str, observado: float) -> dict:
    campo = {"reserva_cobertura_meses": "cobertura", "taxa_endividamento": "endiv"}[kpi_key]
    base = {"endiv": 5.0, "cobertura": 53.3}
    base[campo] = observado
    return base


# ---------------------------------------------------------------------------
# Invariante POR CHAVE — parametrizado sobre todos os gatilhos, não sobre um
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kpi_key", sorted(build_risk_triggers(SCORING)))
def test_gatilho_rompido_emite_o_item_daquela_chave(kpi_key: str):
    gatilho = build_risk_triggers(SCORING)[kpi_key]
    itens = _analyze(**_kwargs(kpi_key, _observado_rompido(kpi_key)))
    assert gatilho.kpi_key in {i.kpi_key for i in itens}, (
        f"{kpi_key} rompido e nenhum ponto urgente o nomeia — "
        f"itens: {[(i.code, i.kpi_key) for i in itens]}"
    )


@pytest.mark.parametrize("kpi_key", sorted(build_risk_triggers(SCORING)))
def test_gatilho_conforme_nao_emite_o_item_daquela_chave(kpi_key: str):
    itens = _analyze(**_kwargs(kpi_key, _observado_conforme(kpi_key)))
    assert kpi_key not in {i.kpi_key for i in itens}


@pytest.mark.parametrize("kpi_key", sorted(build_risk_triggers(SCORING)))
def test_code_e_kpi_key_sao_bijetivos_no_registro(kpi_key: str):
    gatilho = build_risk_triggers(SCORING)[kpi_key]
    itens = _analyze(**_kwargs(kpi_key, _observado_rompido(kpi_key)))
    casados = [i for i in itens if i.kpi_key == kpi_key]
    assert [i.code for i in casados] == [gatilho.code]


# ---------------------------------------------------------------------------
# Por que a forma existencial não serve — medição congelada
# ---------------------------------------------------------------------------


def test_forma_existencial_nao_discrimina():
    """`count(rompidos) > 0 ⟹ len(itens) > 0` fica VERDE com o gatilho rompido e mudo."""
    analyzer = PontosUrgentesAnalyzer(PontosUrgentesConfig.from_scoring(SCORING))
    # `rentabilidade_pct == "N/D"` satisfaz o consequente sem comparar limiar nenhum —
    # é o estado do workspace de referência, onde o invariante antigo é infalsificável.
    itens = analyzer.analyze(
        {
            "taxa_endividamento_pct": 5.0,
            "rentabilidade_pct": "N/D",
            "concentracao_imobiliaria": 82.19,
        },
        {"piso_cobertura_meses": 53.3},
        {},
        _PROTECAO_SEM_GAP,
    )
    assert len(itens) > 0  # a forma existencial passaria...
    assert not [i for i in itens if i.kpi_key]  # ...e nenhum item nomeia gatilho algum


# ---------------------------------------------------------------------------
# Gate estático de cobertura — pega chave nova sem leitor
# ---------------------------------------------------------------------------


def test_toda_chave_sob_o_gate_tem_regra_ou_dispensa_declarada():
    descobertas = chaves_sob_o_gate() - set(build_risk_triggers(SCORING)) - set(DISPENSADAS)
    assert not descobertas, (
        f"chave elegível sem regra de risco e sem dispensa declarada: {sorted(descobertas)}. "
        "Adicione um RiskTrigger ou uma entrada em DISPENSADAS com o motivo — é como este "
        "catálogo nasceu órfão ([[ADR-419]] §D4)."
    )


def test_dispensa_nunca_convive_com_regra_para_a_mesma_chave():
    assert not set(DISPENSADAS) & set(build_risk_triggers(SCORING))


def test_dispensa_declara_motivo_nao_vazio():
    assert all(motivo.strip() for motivo in DISPENSADAS.values())


def test_regra_que_nao_compara_limiar_nao_declara_kpi_key():
    """`seguro_vida` e `rentabilidade_nao_medida` mapeiam órfãos por decisão de domínio."""
    itens = PontosUrgentesAnalyzer(PontosUrgentesConfig.from_scoring(SCORING)).analyze(
        {"taxa_endividamento_pct": 5.0, "rentabilidade_pct": "N/D"},
        {"piso_cobertura_meses": 53.3},
        {},
        None,
    )
    sem_limiar = {"seguro_vida", "rentabilidade_nao_medida"}
    assert {i.kpi_key for i in itens if i.code in sem_limiar} == {None}
