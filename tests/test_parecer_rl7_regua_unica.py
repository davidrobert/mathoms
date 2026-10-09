"""A RL7 tem uma régua só: a do validador, declarada pela REGRA 14 e pela hint de severidade.

Eram três para `$.ratios.concentracao_imobiliaria` — a REGRA 14 em 40/60 (base anterior ao
C11-Fase2), o validador em 50/75 e a hint em "≥50% é Alta" — e um quarto lugar, o ponto
urgente determinístico, que `test_degraus_pareados_com_a_red_line` já pareia com o
validador. A escada é MEDIDA no predicado, nunca copiada para cá: teste que compara o texto
com uma constante espelho sobrevive à mutação dela ([[ADR-340]] §Emenda 2026-10-09).
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path

import pytest
import yaml

from backend.app.services.parecer_manifest import load_manifest, load_persona
from backend.app.services.parecer_red_lines import (
    RED_LINES,
    RL7_LIMIAR_EXIGE_ALTA_PCT,
    RL7_LIMIAR_EXIGE_MEDIA_PCT,
    _severidade_exigida_concentracao,
)
from pipeline.llm.prompts.parecer_planejador import SYSTEM_PROMPT_TEMPLATE, USER_PROMPT_TEMPLATE
from tests.dev.test_prompt_capability_parity import SUPERFICIES

_SCHEMA = Path("config/schemas/parecer_planejador.schema.json")
_MANIFEST = Path("config/prompts/parecer_planejador.yaml")
_HINT_PREFIXO = "Severidade da concentração"
_PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s?%")
_DEGRAU = re.compile(r"acima de (\d+)\s?%([^;.]*)")

# Superfícies que INSTRUEM o modelo — onde uma régua pode ser declarada. As de DADO citam a
# concentração e o rótulo do ponto urgente sem serem régua. Igualdade com o inventário da
# A40.l117: produtor novo sem classificação aqui reprova.
_INSTRUCAO = frozenset({"system_template", "persona", "user_template", "hints"})
_DADO = frozenset({"section_bodies", "eviction_marker", "citation_catalog"})


@functools.lru_cache(maxsize=1)
def _severidades() -> tuple[str, ...]:
    """Enum do schema de saída, do mais grave para o mais leve."""
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return tuple(schema["$defs"]["severidade"]["enum"])


def _exigida(conc: float) -> frozenset[str]:
    e5 = {"ratios": {"concentracao_imobiliaria": conc}}
    return frozenset(_severidade_exigida_concentracao(e5) or ())


@functools.lru_cache(maxsize=1)
def _escada_do_validador() -> tuple[tuple[float, frozenset[str]], ...]:
    """(limiar, severidades aceitas logo acima dele), varrendo 0–100% em centésimos."""
    exigidas = [_exigida(c / 100) for c in range(10_001)]
    return tuple(
        (c / 100, exigidas[c + 1]) for c in range(10_000) if exigidas[c] != exigidas[c + 1]
    )


def _plano(texto: str) -> str:
    return " ".join(texto.split())


def _unidades(bloco: str) -> list[str]:
    """Parágrafos e bullets — a unidade em que uma régua se declara."""
    return [_plano(u) for u in re.split(r"\n\s*\n|\n\s*- ", bloco) if u.strip()]


@functools.lru_cache(maxsize=1)
def _hints_de_secao() -> tuple[str, ...]:
    secoes = load_manifest().sections
    return tuple(_plano(h) for s in secoes for h in s.get("narrative_hints") or [])


def _bullet_rl7() -> str:
    (bullet,) = [u for u in _unidades(SYSTEM_PROMPT_TEMPLATE) if "(RL7)" in u]
    return bullet


def _hint_severidade() -> str:
    (hint,) = [h for h in _hints_de_secao() if h.startswith(_HINT_PREFIXO)]
    return hint


_TEXTOS = {"regra_14": _bullet_rl7, "hint_severidade": _hint_severidade}


def _primeiro_rotulo(clausula: str) -> str | None:
    achados = [(clausula.find(s), s) for s in _severidades() if s in clausula]
    return min(achados)[1] if achados else None


def _escada_declarada(texto: str) -> list[tuple[float, str | None]]:
    """(N, primeiro rótulo do enum) de cada cláusula aberta por "acima de N%"."""
    return [(float(n), _primeiro_rotulo(resto)) for n, resto in _DEGRAU.findall(texto)]


def test_as_constantes_sao_a_escada_medida_no_predicado():
    limiares = [limiar for limiar, _ in _escada_do_validador()]
    assert limiares == [RL7_LIMIAR_EXIGE_MEDIA_PCT, RL7_LIMIAR_EXIGE_ALTA_PCT]


@pytest.mark.parametrize("nome", sorted(_TEXTOS))
def test_o_texto_declara_a_escada_do_validador(nome: str):
    texto, escada = _TEXTOS[nome](), _escada_do_validador()
    declarada = _escada_declarada(texto)
    assert [n for n, _ in declarada] == [limiar for limiar, _ in escada], texto
    for (_, rotulo), (_, aceitas) in zip(declarada, escada):
        assert rotulo in aceitas, f"{nome}: {rotulo!r} ∉ {sorted(aceitas)}"
    percentuais = {float(p.replace(",", ".")) for p in _PCT.findall(texto)}
    assert percentuais <= {limiar for limiar, _ in escada}, f"{nome}: número fora da escada"


def test_o_rotulo_declarado_e_o_piso_do_validador():
    """Decisão de domínio (financial-planner, 2026-10-09): o alvo é o piso, não um acima."""
    pisos = [max(aceitas, key=_severidades().index) for _, aceitas in _escada_do_validador()]
    for nome, texto in _TEXTOS.items():
        assert [rotulo for _, rotulo in _escada_declarada(texto())] == pisos, nome


def test_fronteira_exclusiva_e_meta_ate_o_limiar():
    for texto in (_bullet_rl7(), _hint_severidade()):
        assert not re.search(r"≥|>=|a partir de|abaixo de \d", texto), texto
    assert f"até {RL7_LIMIAR_EXIGE_MEDIA_PCT:.0f}%" in _hint_severidade()


def test_a_regra_14_enumera_as_red_lines_do_validador():
    declaradas = set(re.findall(r"\*\*\((RL\d+)\)", SYSTEM_PROMPT_TEMPLATE))
    assert declaradas == {rl.id for rl in RED_LINES}


def test_a_classificacao_cobre_o_inventario_de_superficies():
    assert _INSTRUCAO | _DADO == SUPERFICIES
    assert not _INSTRUCAO & _DADO


def _declara_regua(unidade: str) -> bool:
    rotulo = any(s in unidade for s in _severidades())
    return "oncentra" in unidade and bool(_PCT.search(unidade)) and rotulo


def _unidades_de_instrucao() -> list[str]:
    persona, _ = load_persona()
    # Sem leitor hoje (A40.l8): coberto para que a cópia já reprove no dia em que ligar.
    manifest = yaml.safe_load(_MANIFEST.read_text(encoding="utf-8"))
    globais = [_plano(h) for h in manifest.get("narrative_hints_global") or []]
    blocos = (SYSTEM_PROMPT_TEMPLATE, USER_PROMPT_TEMPLATE, persona)
    return [u for b in blocos for u in _unidades(b)] + list(_hints_de_secao()) + globais


def test_so_as_duas_ancoras_declaram_regua_de_concentracao():
    declaram = sorted(u for u in _unidades_de_instrucao() if _declara_regua(u))
    assert declaram == sorted([_bullet_rl7(), _hint_severidade()])
