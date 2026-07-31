"""Classificação DERIVADA dos parâmetros de config citáveis (A40.l4 · ADR-355).

Braço A2 da guarda anti-hardcode (os outros quatro estão em
`tests/test_e5n_anti_hardcode.py`, que também hospeda a tabela
`_PARAMS_CITAVEIS` que este módulo confere).

`_PARAMS_CITAVEIS` é curada, e curadoria não força nada: parâmetro citável novo
pode nascer congelado e nenhuma linha o cobre — furo medido na 1ª versão da
guarda (22 linhas escritas à mão, zero forçando entrada). Aqui o universo de
parâmetros de `goals.json` é extraído do **fonte do builder** e cada um tem de
estar classificado, com a classificação verificada contra o comportamento.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import scripts.generate_narratives as e5n
from tests.narrativas_synthetic import (
    GOALS_A,
    e5_payload,
    pin_tenant_config,
    set_path,
    summaries,
)
from tests.test_e5n_anti_hardcode import _PARAMS_CITAVEIS


@pytest.fixture(autouse=True)
def _pinned_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    pin_tenant_config(tmp_path, monkeypatch)


# ───── Braço A2 — a lista é DERIVADA do código, não curada à mão ─────
#
# `_PARAMS_CITAVEIS` é curada. Curadoria não força nada: parâmetro citável novo
# pode nascer congelado e nenhuma linha o cobre — furo medido na 1ª versão desta
# guarda (22 linhas escritas à mão, zero forçando entrada). A derivação fecha o
# furo pelo lado da FONTE: todo parâmetro de `goals.json` que o builder lê é
# extraído do próprio `scripts/generate_narratives.py` e tem de estar
# classificado. Três classes, e cada classe é uma AFIRMAÇÃO VERIFICADA contra o
# comportamento — não um rótulo:
#
#   - linha em `_PARAMS_CITAVEIS`   → o token do valor aparece no texto;
#   - `"gate"`                      → perturbar MUDA algum summary (o parâmetro
#                                     decide se a cláusula existe, mas o número
#                                     impresso não é ele);
#   - `"sem_efeito"`                → perturbar não muda summary nenhum, com a
#                                     razão medida escrita.
#
# Congelar um literal move o parâmetro de "citado" para "sem efeito": a linha do
# braço A fica vermelha (token ausente) E a classificação passa a mentir.
# Parâmetro NOVO sem classificação deixa `test_todo_parametro_...` vermelho.

_BUILDER_SRC = Path(e5n.__file__).read_text(encoding="utf-8")

_BLOCO_VAR_RE = re.compile(r'^\s*(\w+)\s*=\s*goals_cfg\.get\(\s*"([^"]+)"', re.M)


def _bloco_por_var() -> dict[str, str]:
    return dict(_BLOCO_VAR_RE.findall(_BUILDER_SRC))


def _config_leaves() -> set[tuple[str, ...]]:
    """Parâmetros de ``goals.json`` que o builder lê, extraídos do fonte."""
    blocos = _bloco_por_var()
    folhas = {
        (bloco, chave)
        for var, bloco in blocos.items()
        for chave in re.findall(rf'\b{re.escape(var)}\.get\(\s*"([^"]+)"', _BUILDER_SRC)
    }
    com_folha = {bloco for bloco, _ in folhas}
    # Bloco sem folha é lido como VALOR, não como namespace (`risks_projection`,
    # `top5_decisoes_projection`) — é ele mesmo o parâmetro.
    diretos = set(re.findall(r'goals_cfg\.get\(\s*"([^"]+)"', _BUILDER_SRC))
    return folhas | {(nome,) for nome in diretos - com_folha}


@dataclass(frozen=True)
class EfeitoDeclarado:
    """Classificação de um parâmetro não-citado, com o valor que a verifica."""

    efeito: str  # "gate" | "sem_efeito"
    razao: str
    alternativo: Any


def _gate(razao: str, alternativo: Any) -> EfeitoDeclarado:
    return EfeitoDeclarado("gate", razao, alternativo)


def _sem_efeito(razao: str, alternativo: Any) -> EfeitoDeclarado:
    return EfeitoDeclarado("sem_efeito", razao, alternativo)


_EFEITO_DECLARADO: dict[tuple[str, ...], EfeitoDeclarado] = {
    ("tributario", "regime"): _gate(
        "sinal de perfil declarado (ADR-236 §D5): `None` troca o s8 pelo estado "
        "pendente. Não é número impresso.",
        None,
    ),
    ("tributario", "contador_nome"): _gate(
        "presença liga a cláusula de contador; o NOME nunca é impresso — é PII "
        "de terceiro (ADR-319 · ADR-355 §D9).",
        None,
    ),
    ("risks_projection",): _gate(
        "lista de riscos: vazia troca o s9 pelo empty state. O que o texto cita "
        "são os nomes, que são input do usuário, não parâmetro.",
        [],
    ),
    ("top5_decisoes_projection",): _gate(
        "lista de decisões: muda a contagem e os títulos citados no s10.",
        [{"title": "Outra decisão estratégica"}],
    ),
    ("alocacao_alvo", "rebalanceamento"): _sem_efeito(
        "vira `aloc_rebalanceamento`, consumido pelo narrador do chart "
        "`alocacao_atual_vs_alvo`; nenhum summary o cita.",
        "trimestral",
    ),
    ("independencia_financeira", "renda_passiva_meta_mensal"): _sem_efeito(
        "vira `pct_renda_passiva_meta` (progresso), consumido fora de summaries.",
        23_100.0,
    ),
    ("independencia_financeira", "trs_pct"): _sem_efeito(
        "yield-alvo/TRS é citado em `perfil_familia.right`, não em summary — o "
        "s7 cita a SWR, que é outro conceito (ADR-191 §Emenda FP-03). O default "
        "`5.0` do builder é inalcançável: `if_projector` levanta ValueError sem "
        "`trs_pct`, então o E5 nem chega ao E5.N.",
        8.0,
    ),
    ("tributario", "contador_canal_pagamento"): _sem_efeito(
        "só decora a cláusula quando há honorário informado, e `contador_mensal` "
        "não existe no bundle de hoje (§D7) — dormente junto com ele.",
        "via PIX mensal",
    ),
    ("tributario", "holding_avaliacao_prazo"): _sem_efeito(
        "fallback legado, lido só quando `holding_prazo_meses` falta.",
        "18 meses",
    ),
    ("tributario", "regime_obs"): _sem_efeito(
        "fallback legado de `regime_label`; com o label presente não é lido.",
        "observação legada",
    ),
    ("fase_f1f2", "viagens_anuais_estimadas"): _sem_efeito(
        "a cláusula de viagens exige as TRÊS chaves juntas (`viagens` E "
        "(`min` OU `max`)), então nenhuma muda o texto isolada; e o bundle de "
        "produção não popula `fase_f1f2` (resíduo do Modo USA, ADR-168). O "
        "destino `s5` é órfão — não é entregue a seção nenhuma.",
        3,
    ),
    ("fase_f1f2", "custo_viagem_minimo"): _sem_efeito(
        "idem `viagens_anuais_estimadas` — gate conjunto, bloco ausente em "
        "produção, summary órfão.",
        7_400.0,
    ),
    ("fase_f1f2", "custo_viagem_maximo"): _sem_efeito(
        "idem `viagens_anuais_estimadas` — gate conjunto, bloco ausente em "
        "produção, summary órfão.",
        18_300.0,
    ),
}


def _paths_com_linha() -> set[tuple[str, ...]]:
    return {p.path for p in _PARAMS_CITAVEIS if p.fonte == "goals"}


def test_todo_parametro_de_config_lido_pelo_builder_esta_classificado() -> None:
    """Nenhum parâmetro de `goals.json` escapa: linha citável OU efeito declarado."""
    classificados = _paths_com_linha() | set(_EFEITO_DECLARADO)
    faltando = sorted(_config_leaves() - classificados)
    assert not faltando, (
        f"parâmetro de config lido por `load_metrics_from_e5` sem classificação: "
        f"{faltando}. Se o texto imprime o valor, adicione linha em "
        "_PARAMS_CITAVEIS (com token e dois valores); se só liga/desliga "
        "cláusula, declare `_gate(...)`; se nenhum summary o usa, declare "
        "`_sem_efeito(...)` — sempre com a razão MEDIDA."
    )


def test_classificacao_declarada_nao_descreve_parametro_que_saiu_do_builder() -> None:
    """Classificação órfã é declaração morta — apaga junto com a leitura."""
    orfas = sorted(set(_EFEITO_DECLARADO) - _config_leaves())
    assert not orfas, f"efeito declarado para parâmetro que o builder não lê mais: {orfas}"


def _summaries_com_leaf(path: tuple[str, ...], valor: Any) -> dict[str, str]:
    goals = copy.deepcopy(GOALS_A)
    set_path(goals, path, valor)
    return summaries(e5_payload(), goals)


@pytest.mark.parametrize(
    "path", sorted(_EFEITO_DECLARADO), ids=lambda p: f"{_EFEITO_DECLARADO[p].efeito}-{'.'.join(p)}"
)
def test_efeito_declarado_bate_com_o_comportamento(path: tuple[str, ...]) -> None:
    """`gate` tem de mudar algum summary; `sem_efeito` tem de mudar nenhum."""
    declarado = _EFEITO_DECLARADO[path]
    base = summaries(e5_payload(), GOALS_A)
    mudou = sorted(
        k for k, v in _summaries_com_leaf(path, declarado.alternativo).items() if base[k] != v
    )
    if declarado.efeito == "gate":
        assert mudou, (
            f"`{'.'.join(path)}` declarado `gate` mas perturbá-lo não muda summary "
            "nenhum — a razão escrita não descreve o código."
        )
        return
    assert not mudou, (
        f"`{'.'.join(path)}` declarado `sem_efeito` mas perturbá-lo muda {mudou}. "
        "Se o valor é impresso, a classificação certa é linha em _PARAMS_CITAVEIS."
    )
