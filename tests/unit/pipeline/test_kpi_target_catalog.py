"""Alvo de KPI é derivado, não autorado (§r7 PE-2/FP-6).

Fixture sintética PII-free reproduz o par medido: `concentracao_imobiliaria`
byte-idêntico em dois runs, sobre o qual o parecer publicou `< 30%` e depois
`< 35%` — atravessando o valor observado (34,86), convertendo violação em
conformidade sem o dado mudar.

O teste que importa é o de **mutação**: mudar a fonte tem de mover o alvo, e
mudar o que o LLM diria **não** tem de mover — é isso que prova que a procedência
saiu do modelo. Teste que só afirma "target existe" passa igual com o LLM
autorando.
"""

from __future__ import annotations

from typing import Any, Optional

from pipeline.domain.services.kpi_target_catalog import (
    METRICA_KEYS,
    PROCEDENCIA_CANONICO,
    PROCEDENCIA_GOAL,
    build_kpi_targets,
)

# Valor observado do par r5/r7 — o número que o alvo do LLM atravessou.
CONCENTRACAO_OBSERVADA = 34.86
ALVO_RF_DECLARADO = 51.55
# O que o LLM publicou no r7 para renda fixa: mais frouxo que o declarado.
ALVO_RF_DO_LLM = 55.0

SCORING: dict[str, Any] = {"thresholds_alertas": {"endividamento_maximo_pct": 20}}


def _e5(
    *, alvo_rf: Optional[float] = ALVO_RF_DECLARADO, meses_alvo: Optional[int] = 18
) -> dict[str, Any]:
    comparaveis: list[dict[str, Any]] = []
    if alvo_rf is not None:
        # Ordem propositalmente NÃO-canônica: o resolver casa por `classe`, e um
        # join por índice passaria neste payload e quebraria no próximo.
        comparaveis = [
            {"classe": "acoes_br", "alvo_pct": 25.77, "atual_pct": 13.04},
            {"classe": "renda_fixa", "alvo_pct": alvo_rf, "atual_pct": 82.30},
        ]
    return {
        "ratios": {"concentracao_imobiliaria": CONCENTRACAO_OBSERVADA},
        "reserva_emergencia": {"meses_alvo": meses_alvo},
        "goals": {"alocacao_alvo": {"derived": {"comparaveis": comparaveis}}},
    }


def test_alvo_e_o_limiar_canonico_nao_o_do_llm() -> None:
    alvo = build_kpi_targets(_e5(), scoring=SCORING)["concentracao_imobiliaria"]

    assert alvo["limiar"] == 50.0, "o canon é 50% (ADR-340); 30/35 eram fabricação do LLM"
    assert alvo["procedencia"] == PROCEDENCIA_CANONICO
    # Sob o canon a família está CONFORME — o r5 afirmou violação sobre este dado.
    assert CONCENTRACAO_OBSERVADA < alvo["limiar"]


def test_alvo_declarado_pela_familia_nao_e_afrouxado() -> None:
    """FP-6: o parecer publicou 55% contra os 51,55% que a família declarou."""
    alvo = build_kpi_targets(_e5(), scoring=SCORING)["alocacao_renda_fixa"]

    assert alvo["limiar"] == ALVO_RF_DECLARADO
    assert alvo["procedencia"] == PROCEDENCIA_GOAL
    assert alvo["limiar"] < ALVO_RF_DO_LLM, "alvo publicado nunca é mais frouxo que o declarado"


# A mutação é a prova. Sem ela, um resolver que retornasse constantes hardcoded
# passaria nos dois testes acima.
def test_mutacao_na_fonte_move_o_alvo() -> None:
    padrao = build_kpi_targets(_e5(), scoring=SCORING)
    mutado_goal = build_kpi_targets(_e5(alvo_rf=40.0), scoring=SCORING)
    mutado_canon = build_kpi_targets(_e5(), scoring=SCORING, concentracao_alerta_pct=45.0)

    assert mutado_goal["alocacao_renda_fixa"]["limiar"] == 40.0
    assert padrao["alocacao_renda_fixa"]["limiar"] != mutado_goal["alocacao_renda_fixa"]["limiar"]
    assert mutado_canon["concentracao_imobiliaria"]["limiar"] == 45.0
    assert (
        padrao["concentracao_imobiliaria"]["limiar"]
        != mutado_canon["concentracao_imobiliaria"]["limiar"]
    )


def test_alvo_nao_depende_do_valor_observado() -> None:
    """PE-2 direto: o observado muda, o alvo não. O inverso é o defeito medido."""
    e5_a = _e5()
    e5_b = _e5()
    e5_b["ratios"]["concentracao_imobiliaria"] = 61.2

    alvo_a = build_kpi_targets(e5_a, scoring=SCORING)["concentracao_imobiliaria"]
    alvo_b = build_kpi_targets(e5_b, scoring=SCORING)["concentracao_imobiliaria"]

    assert alvo_a == alvo_b


def test_join_por_classe_e_nao_por_indice() -> None:
    e5 = _e5()
    e5["goals"]["alocacao_alvo"]["derived"]["comparaveis"].reverse()

    alvo = build_kpi_targets(e5, scoring=SCORING)["alocacao_renda_fixa"]

    assert alvo["limiar"] == ALVO_RF_DECLARADO


def test_fonte_ausente_vira_orfao_com_motivo_nunca_numero() -> None:
    alvos = build_kpi_targets(_e5(alvo_rf=None, meses_alvo=None), scoring={})

    for chave in ("alocacao_renda_fixa", "reserva_cobertura_meses", "taxa_endividamento"):
        assert alvos[chave]["limiar"] is None, f"{chave} sem fonte não pode publicar número"
        assert alvos[chave]["motivo"], f"{chave} órfão precisa dizer por quê"


def test_orfaos_por_decisao_de_dominio_nunca_ganham_alvo() -> None:
    """TRS (ADR-191 §D5), proteção (ADR-387) e poupança (RV2-24) são órfãos por
    decisão, não por lacuna — publicar número aqui seria regressão, não melhoria."""
    alvos = build_kpi_targets(_e5(), scoring=SCORING)

    for chave in ("carteira_trs", "protecao_cobertura", "taxa_poupanca_recorrente"):
        assert alvos[chave]["limiar"] is None
        assert alvos[chave]["motivo"]


def test_todo_kpi_do_vocabulario_tem_entrada() -> None:
    """Chave no enum sem entrada no catálogo é alvo que o LLM seleciona e ninguém
    resolve — o campo voltaria a ser autorado por omissão."""
    alvos = build_kpi_targets(_e5(), scoring=SCORING)

    assert set(alvos) == set(METRICA_KEYS)
    for chave, alvo in alvos.items():
        assert alvo["observado_path"].startswith("$."), chave
        assert alvo["base"], chave
        # Invariante: ou tem procedência declarada, ou tem motivo. Nunca nenhum.
        assert bool(alvo["procedencia"]) != bool(alvo["motivo"]), chave
