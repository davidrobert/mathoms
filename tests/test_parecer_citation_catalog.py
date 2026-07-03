"""Catálogo de citação E5→E6 — consistência com o verificador (A26.l1)."""

from __future__ import annotations

import pytest

from backend.app.services.parecer_citation_catalog import (
    _PRIORITY_ROOTS,
    build_citation_catalog,
    render_citation_catalog,
)
from backend.app.services.parecer_manifest import load_manifest
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown
from pipeline.llm.value_formatter import format_value
from tests.test_parecer_planejador_golden import make_workspace_e5


@pytest.fixture(scope="module")
def whitelist() -> frozenset[str]:
    return load_manifest().tools_section_whitelist


def test_every_entry_roundtrips_against_verifier(whitelist):
    e5 = make_workspace_e5()
    entries = build_citation_catalog(e5, section_whitelist=whitelist)
    assert entries, "E5 sintético rico deve render pelo menos algumas folhas monetárias"
    drill = PlannerDrillDown(e5_data=e5, section_whitelist=whitelist, format_hints={})
    for entry in entries:
        result = drill.get_e5_jsonpath(entry.path)
        assert result.found, f"path {entry.path} não resolve no verificador (whitelist/null)"
        # ADR-296: display_value é format_value(value, 'brl') — round-trip determinístico.
        assert entry.display_value == format_value(
            result.value, "brl"
        ), f"display de {entry.path} divergiu do valor resolvido"


def test_no_percent_or_count_leaves_listed(whitelist):
    entries = build_citation_catalog(make_workspace_e5(), section_whitelist=whitelist)
    for entry in entries:
        leaf = entry.path.rsplit(".", 1)[-1].lower()
        assert "pct" not in leaf and "percent" not in leaf, f"folha percentual citada: {entry.path}"


def test_all_roots_in_whitelist(whitelist):
    entries = build_citation_catalog(make_workspace_e5(), section_whitelist=whitelist)
    for entry in entries:
        assert entry.root in whitelist, f"raiz {entry.root} fora da whitelist"


def test_priority_roots_rank_first(whitelist):
    entries = build_citation_catalog(make_workspace_e5(), section_whitelist=whitelist)
    roots_in_order = [e.root for e in entries]
    if "reserva_emergencia" in roots_in_order and "irpf_kpis" in roots_in_order:
        assert roots_in_order.index("reserva_emergencia") < roots_in_order.index("irpf_kpis")


def test_empty_when_no_money_leaves(whitelist):
    e5 = {"score": {"valor": None}, "ratios": {"rentabilidade_pct": "4.70"}}
    entries = build_citation_catalog(e5, section_whitelist=whitelist)
    assert entries == []
    assert render_citation_catalog(entries, max_bytes=1600) == ""


def _has_no_orphan_root(lines: list[str]) -> bool:
    return all(
        i + 1 < len(lines) and lines[i + 1].startswith("- ")
        for i, ln in enumerate(lines)
        if ln.startswith("**") and ln.endswith("**")
    )


def test_truncation_preserves_priority_no_orphan(whitelist):
    """Payload rico + budget apertado: catálogo trunca cauda, nunca deixa raiz órfã."""
    entries = build_citation_catalog(make_workspace_e5(), section_whitelist=whitelist)
    assert len(entries) >= 4
    lines = render_citation_catalog(entries, max_bytes=260).splitlines()
    assert _has_no_orphan_root(lines)
    roots = [ln.strip("*") for ln in lines if ln.startswith("**")]
    assert roots and roots[0] in set(_PRIORITY_ROOTS)


def test_max_entries_cap(whitelist):
    entries = build_citation_catalog(
        make_workspace_e5(), section_whitelist=whitelist, max_entries=3
    )
    assert len(entries) == 3


# -----------------------------------------------------------------------
# A26.l7 — cobertura de folhas de LISTA via [idx].subkey escalar
# -----------------------------------------------------------------------


def test_list_element_leaves_are_catalogued(whitelist):
    """E5 sintético tem $.investimentos.tabela_classes (lista) — agora citável."""
    entries = build_citation_catalog(
        make_workspace_e5(), section_whitelist=whitelist, max_entries=60
    )
    list_paths = [e.path for e in entries if "[" in e.path]
    assert list_paths, "nenhuma folha de lista catalogada (regressão A26.l7)"
    assert all(p.endswith("].valor") for p in list_paths)


def test_list_path_resolve_para_escalar_unico_nao_lista_inteira(whitelist):
    """[idx].valor → exatamente 1 folha numérica (não [*] que coletaria a lista)."""
    e5 = make_workspace_e5()
    entries = build_citation_catalog(e5, section_whitelist=whitelist, max_entries=60)
    drill = PlannerDrillDown(e5_data=e5, section_whitelist=whitelist, format_hints={})
    path = next(e.path for e in entries if "[" in e.path)
    val = drill.get_e5_jsonpath(path).value
    assert isinstance(val, (int, float)) and not isinstance(
        val, bool
    ), f"{path} resolveu para {type(val).__name__} (esperado escalar único, não lista)"


def test_list_cap_top_k_por_valor_com_indice_original(whitelist):
    """Lista de 40 itens → ≤ _MAX_LIST_ITEMS entradas, os de MAIOR valor, índice original."""
    from backend.app.services.parecer_citation_catalog import _MAX_LIST_ITEMS

    classes = [{"categoria": f"c{i}", "valor": i * 1000} for i in range(40)]
    e5 = {"investimentos": {"tabela_classes": classes}}
    entries = build_citation_catalog(e5, section_whitelist=whitelist, max_entries=60)
    idxs = sorted(int(e.path.split("[")[1].split("]")[0]) for e in entries)
    assert len(idxs) == _MAX_LIST_ITEMS
    assert idxs == [35, 36, 37, 38, 39], "top-K deve ser por maior valor, com índice original"


# -----------------------------------------------------------------------
# A28.l10 — tipo de folha por nome de campo (fonte do dispatch do finalize)
# -----------------------------------------------------------------------


def test_ancora_format_hint_por_tipo_de_folha():
    """Dogfood 72883bde: prob/idade viravam R$ — o hint vem do nome do campo
    (a folha conhece seu campo), nunca de heurística sobre o valor."""
    from backend.app.services.parecer_citation_catalog import ancora_format_hint

    assert ancora_format_hint("$.if_monte_carlo.prob_if_ate_idade_meta") == "prob_pct"
    assert ancora_format_hint("$.if_monte_carlo.idade_meta_usada") == "anos"
    assert ancora_format_hint("$.ratios.taxa_poupanca_recorrente_pct") == "pct"
    assert ancora_format_hint("$.reserva_emergencia.cobertura_meses") == "meses"
    assert ancora_format_hint("$.irpf_kpis.dependentes_count") == "int"
    assert ancora_format_hint("$.investimentos.n_imoveis_total") == "int"
    assert ancora_format_hint("$.reserva_emergencia.total_liquida") == "brl"
    assert ancora_format_hint("$.reserva_emergencia.nivel_6_meses") == "brl"
    assert ancora_format_hint("$.investimentos.tabela_classes[2].valor") == "brl"
    # fallback: folha sem tipo conhecido nunca ganha prefixo R$
    assert ancora_format_hint("$.goals.p50_ano_if") == "string"
