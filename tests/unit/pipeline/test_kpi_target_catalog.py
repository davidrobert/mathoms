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

import pytest

from pipeline.domain.services.kpi_target_catalog import (
    METRICA_KEYS,
    PROCEDENCIA_CANONICO,
    PROCEDENCIA_GOAL,
    KpiTarget,
    build_kpi_targets,
)

# Valor observado do par r5/r7 — o número que o alvo do LLM atravessou.
CONCENTRACAO_OBSERVADA = 34.86
ALVO_RF_DECLARADO = 51.55
# O que o LLM publicou no r7 para renda fixa: mais frouxo que o declarado.
ALVO_RF_DO_LLM = 55.0

SCORING: dict[str, Any] = {"thresholds_alertas": {"endividamento_maximo_pct": 20}}


# `base_denominador` acompanha o payload porque o produtor SEMPRE o publica
# (`reserva_emergencia_calculator.py:278`); fixture sem ele mediria o ramo de série
# anterior em vez do corrente.
def _e5(
    *,
    alvo_rf: Optional[float] = ALVO_RF_DECLARADO,
    meses_alvo: Optional[int] = 18,
    base_denominador: str = "custo_essencial",
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
        "reserva_emergencia": {"meses_alvo": meses_alvo, "base_denominador": base_denominador},
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

    for chave in (
        "carteira_trs",
        "protecao_custo_premio",
        "taxa_poupanca_recorrente",
        "if_prazo_ano",
        "aliquota_efetiva_ir",
    ):
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


# ---------------------------------------------------------------------------
# A40.l80 §Correções C14 — base DECLARADA tem de ser o denominador USADO
# ---------------------------------------------------------------------------


# Mede o discriminador NO produtor em vez de copiar os literais para cá: copiados,
# teste e catálogo compartilhariam a mesma crença, e regime novo no produtor
# nasceria com o catálogo calado e o teste verde.
def _regimes_do_produtor() -> dict[str, str]:
    """Discriminador que o produtor emite em cada regime, medido nele."""
    from pipeline.domain.services.reserva_emergencia_calculator import _base_from_window

    janela = {"despesa_mensal_media": 10_000.0}
    com = {**janela, "despesa_mensal_essencial": 6_000.0}
    sem = {**janela, "despesa_mensal_essencial": 0.0}
    kw = {"janela": "full", "janela_meses": 12}
    return {
        "essencial": _base_from_window(com, **kw).base_denominador,
        "fallback": _base_from_window(sem, **kw).base_denominador,
    }


def _base_da_reserva(**kw: Any) -> str:
    return build_kpi_targets(_e5(**kw), scoring=SCORING)["reserva_cobertura_meses"]["base"]


# Mata: `base` fixa "essencial" sobre denominador de despesa TOTAL. O defeito só
# existe no regime de fallback, e o dogfood roda em `custo_essencial` — o golden
# nunca o exercitaria, e foi por isso que ele sobreviveu.
def test_base_da_reserva_segue_o_discriminador_que_o_produtor_publica() -> None:
    """Cada regime do produtor publica a base que ele de fato dividiu."""
    regimes = _regimes_do_produtor()

    essencial = _base_da_reserva(base_denominador=regimes["essencial"])
    fallback = _base_da_reserva(base_denominador=regimes["fallback"])

    assert essencial == "despesa_essencial_mensal"
    assert fallback == "despesa_mensal_media"
    assert essencial != fallback, "os dois regimes publicariam a mesma base — é o C14 de volta"


# Fecha a CLASSE, não a instância: regime novo no produtor não pode cair calado no
# ramo de série anterior, que é o que um `.get()` com default faria.
def test_todo_regime_do_produtor_e_conhecido_pelo_catalogo() -> None:
    """Nenhum discriminador que o produtor emite vira `indeterminado`."""
    from pipeline.domain.services.kpi_target_catalog import _BASE_POR_DENOMINADOR

    for regime, discriminador in _regimes_do_produtor().items():
        assert discriminador in _BASE_POR_DENOMINADOR, f"regime {regime} desconhecido do catálogo"


def test_discriminador_ausente_nao_afirma_essencialidade() -> None:
    """Artefato de série anterior (ADR-412 §D8): ausência é "não sei", nunca essencial."""
    e5 = _e5()
    del e5["reserva_emergencia"]["base_denominador"]

    base = build_kpi_targets(e5, scoring=SCORING)["reserva_cobertura_meses"]["base"]

    assert base == "despesas_mensais"
    assert "essencial" not in base


# Casa a base ao NOME DO CAMPO que o produtor divide, não a um rótulo escolhido à
# mão — declarar "ativa" sobre um pct que sai de `renda_anual_liquida_brl` é o modo
# de falha que a ADR-399 existe para impedir.
def test_protecao_declara_a_renda_pela_qual_o_produtor_divide() -> None:
    """A base da proteção nomeia um campo real de `ProtecaoInput`."""
    from pipeline.domain.services.protecao_analyzer import ProtecaoInput

    # A chave passou a nomear o conceito que o payload de fato publica
    # (prêmio/renda), não "cobertura" — que não tem agregado no schema, por desenho
    # da [[ADR-387]]. A asserção de base segue idêntica.
    base = build_kpi_targets(_e5(), scoring=SCORING)["protecao_custo_premio"]["base"]

    assert f"{base}_brl" in ProtecaoInput.__dataclass_fields__, f"`{base}` não nomeia campo"
    assert base != "renda_anual_ativa"


_COMUM = {"observado_path": "$.ratios.x", "base": "b", "unidade": "pct", "rotulo": "X"}

# Estados que o construtor tem de recusar. O 1º é o defeito que a ADR-399 fecha e
# que a suíte antiga aceitava calada: os dois invariantes existentes olham
# `procedencia`/`motivo` sem pinar `limiar`, e o do golden pina `operador`/`ref` sem
# pinar `procedencia`. Como os dois predicados colapsam em 1 bit no produtor,
# nenhuma mutação de payload discrimina qual chave o consumidor usou.
_ESTADOS_PROIBIDOS = [
    ("numero sem fonte", {"limiar": 42.0, "operador": "<", "ref": "algum.lugar"}),
    ("fonte sem numero", {"procedencia": PROCEDENCIA_CANONICO}),
    (
        "resolvido e orfao",
        {
            "limiar": 42.0,
            "operador": "<",
            "procedencia": PROCEDENCIA_CANONICO,
            "ref": "r",
            "motivo": "também órfão",
        },
    ),
]


@pytest.mark.parametrize("caso,kwargs", _ESTADOS_PROIBIDOS, ids=[c for c, _ in _ESTADOS_PROIBIDOS])
def test_estado_sem_procedencia_e_irrepresentavel(caso: str, kwargs: dict) -> None:
    with pytest.raises(ValueError):
        KpiTarget(**_COMUM, **kwargs)


def test_estados_legitimos_continuam_construiveis() -> None:
    KpiTarget(**_COMUM, limiar=1.0, operador="<", procedencia=PROCEDENCIA_CANONICO, ref="r")
    KpiTarget(**_COMUM, motivo="sem alvo canônico")


def test_todo_kpi_publica_rotulo_proprio() -> None:
    """O nome da métrica sai do catálogo, não do LLM. Rótulo autorado não é
    gateável, e ele carrega domínio: cobrir 100% da despesa *essencial* é o marco
    de segurança, não a independência — o qualificador é a diferença entre as duas."""
    alvos = build_kpi_targets(_e5(), scoring=SCORING)

    rotulos = {chave: alvo["rotulo"] for chave, alvo in alvos.items()}
    assert all(rotulos.values()), f"chave sem rótulo: {[k for k, v in rotulos.items() if not v]}"
    assert len(set(rotulos.values())) == len(rotulos), "dois KPIs com o mesmo rótulo"
    assert "essencial" in rotulos["renda_passiva_cobertura"].lower()


def test_cobertura_de_renda_passiva_sem_medicao_e_orfa_nunca_zero() -> None:
    """`status != "ok"` significa insumo faltando, não renda passiva ausente.
    Publicar 0% ali é a leitura mais assustadora que o relatório sabe emitir, e
    seria falsa — ausência declarada vence zero medido."""
    medido = {
        "ratios": {"rentabilidade": {"status": "ok", "cobertura_despesa_essencial_pct": 15.06}}
    }
    sem_insumo = {
        "ratios": {"rentabilidade": {"status": "sem_irpf", "cobertura_despesa_essencial_pct": 0.0}}
    }

    com = build_kpi_targets({**_e5(), **medido}, scoring=SCORING)["renda_passiva_cobertura"]
    sem = build_kpi_targets({**_e5(), **sem_insumo}, scoring=SCORING)["renda_passiva_cobertura"]

    assert com["limiar"] == 100.0 and com["procedencia"] == PROCEDENCIA_CANONICO
    assert com["operador"] == ">=" and com["base"] == "despesa_essencial_mensal_12m"
    assert sem["limiar"] is None and sem["motivo"], "status degradado tem de suprimir o alvo"
