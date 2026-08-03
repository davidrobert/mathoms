"""Prazo IF não projetável → ausência explícita, nunca sentinela (RV2-01).

A sentinela ``999`` de ``IFProjector._solve_prazo`` era somada à idade do
titular e ao ano-base, e o resultado (idade 1040, ano 3025) chegava ao payload
E5. Como ``if_monte_carlo`` está em ``_PRIORITY_ROOTS`` do catálogo de citação
e ``idade_meta_usada`` é folha citável com hint "anos", o parecer podia ancorar
uma recomendação em "IF aos 1040 anos" — métrica fabricada.

O workspace dogfood tem ``meta_aporte_mensal = 0``: é exatamente o caso que
não converge, e por isso serve de fixture de regressão fim-a-fim.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.services.parecer_citation_catalog import build_citation_catalog
from backend.app.services.parecer_manifest import load_manifest
from tests.pipeline_golden_substrate import (
    load_fixture,
    run_dogfood_pipeline,
    write_e5_config,
)

_DOGFOOD = Path(__file__).parent / "fixtures" / "pipeline_golden" / "dogfood"

# Nenhum humano vive além disto; qualquer idade acima é aritmética sobre
# sentinela, não medição.
_IDADE_MAXIMA_PLAUSIVEL = 120
_ANO_MAXIMO_PLAUSIVEL = 2200


@pytest.fixture(scope="module")
def e5_sem_convergencia(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("if_horizonte_ausente")
    write_e5_config(root)
    return run_dogfood_pipeline(
        root,
        raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
        e2_extracts={
            "fict_a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
            "fict_b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
        },
    )


def test_fixture_realmente_nao_converge(e5_sem_convergencia):
    """Guarda o pressuposto: se o dogfood passar a convergir, este arquivo mente."""
    goals = e5_sem_convergencia["goals"]
    assert goals["prazo_anos_realista"] is None
    assert goals["motivo_prazo_indefinido"]


def test_goals_nao_projeta_idade_nem_ano(e5_sem_convergencia):
    goals = e5_sem_convergencia["goals"]
    assert goals["idade_titular_if"] is None
    assert goals["ano_if"] is None


def test_monte_carlo_nao_afirma_idade_meta(e5_sem_convergencia):
    """Sem idade-meta não há 'probabilidade até a idade X' — nem alvo, nem prob."""
    mc = e5_sem_convergencia["if_monte_carlo"]
    assert mc["idade_meta_usada"] is None
    assert mc["prob_if_ate_idade_meta"] is None


def test_cenario_conjuge_nao_projeta_horizonte(e5_sem_convergencia):
    cenarios = e5_sem_convergencia.get("cenarios_conjuge") or {}
    for cenario in cenarios.get("cenarios", []):
        assert cenario["prazo_if_anos"] is None
        assert cenario["ano_if"] is None
        assert cenario["idade_titular"] is None
        assert "999" not in cenario["resumo"]


def _children(node):
    """Pares (sufixo_do_path, filho) de dict/lista; vazio para folha."""
    if isinstance(node, dict):
        return [(f".{key}", value) for key, value in node.items()]
    if isinstance(node, list):
        return [(f"[{i}]", value) for i, value in enumerate(node)]
    return []


def _walk(node, path="$"):
    filhos = _children(node)
    if not filhos:
        yield path, node
        return
    for sufixo, filho in filhos:
        yield from _walk(filho, path + sufixo)


def test_nenhuma_idade_ou_ano_implausivel_no_payload(e5_sem_convergencia):
    """Gate largo: pega a sentinela reaparecendo por qualquer caminho novo."""
    ofensores = []
    for path, value in _walk(e5_sem_convergencia):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        leaf = path.rsplit(".", 1)[-1].split("[", 1)[0].lower()
        if "idade" in leaf and value > _IDADE_MAXIMA_PLAUSIVEL:
            ofensores.append((path, value))
        if leaf.startswith("ano_") and value > _ANO_MAXIMO_PLAUSIVEL:
            ofensores.append((path, value))
    assert not ofensores, f"aritmética sobre sentinela vazou para o payload: {ofensores}"


def test_idade_meta_ausente_nao_vira_ancora_citavel(e5_sem_convergencia):
    """O parecer não pode ancorar em campo que a projeção não produziu."""
    whitelist = load_manifest().tools_section_whitelist
    paths = {
        e.path for e in build_citation_catalog(e5_sem_convergencia, section_whitelist=whitelist)
    }
    assert "$.if_monte_carlo.idade_meta_usada" not in paths
    assert "$.if_monte_carlo.prob_if_ate_idade_meta" not in paths
