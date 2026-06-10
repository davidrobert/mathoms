"""Goldens do renderer LLM linearizado (ADR-281 · A25.l4 F7): formato por nó,
anomaly-first, colapso de subárvore limpa, determinismo e teto de tokens."""

from __future__ import annotations

from pipeline.domain.services.lineage_render_llm import (
    DEFAULT_TOKEN_BUDGET,
    render_lineage_linear,
)

_STAGE = "E5"
_KEY = "analise_financeira"
_RULE = {"ref": "pipeline.domain.services.x:Calc.calculate", "adr": "ADR-145"}


def _leaf(field: str, value) -> dict:
    return {
        "node_type": "no_lineage",
        "stage": _STAGE,
        "artifact_key": _KEY,
        "field": field,
        "value": value,
    }


def _node(field: str, value: str, children: list[dict], *, edge="aggregation", **extra) -> dict:
    return {
        "node_type": "lineage",
        "stage": _STAGE,
        "artifact_key": _KEY,
        "field": field,
        "value": value,
        "label": f"Label {field}",
        "transform": f"transform {field}",
        "edge_type": edge,
        "rule_ref": dict(_RULE),
        "inputs": children,
        **extra,
    }


def _clean_tree() -> dict:
    bruto = _node(
        "patrimonio.bruto",
        "730000.00",
        [
            _leaf("patrimonio.composicao[a].valor", 600000.0),
            _leaf("patrimonio.composicao[b].valor", 130000.0),
        ],
    )
    return _node(
        "patrimonio.liquido",
        "580000.00",
        [bruto, _leaf("patrimonio.dividas", 150000.0)],
        edge="formula",
    )


def test_clean_tree_collapses_clean_subtree_and_keeps_root_expanded():
    expected = "\n".join(
        [
            "[1] patrimonio.liquido = 580000.00 | Label patrimonio.liquido | "
            "transform patrimonio.liquido [formula]",
            "    inputs: #2 #3",
            f"    rule: {_RULE['ref']} ({_RULE['adr']})",
            "[2] patrimonio.bruto = 730000.00 ✓ (3 nós, sem anomalia)",
            "[3] patrimonio.dividas = 150000.0 | folha: E5/analise_financeira",
        ]
    )
    assert render_lineage_linear(_clean_tree()) == expected


def test_conservation_anomaly_emits_warning_block_first():
    tree = _clean_tree()
    tree["inputs"][0]["value"] = "780000.00"  # Σ inputs continua 730000.00
    lines = render_lineage_linear(tree).splitlines()
    assert lines[0] == (
        "[2] patrimonio.bruto = 780000.00 | Label patrimonio.bruto | "
        "transform patrimonio.bruto [aggregation]"
    )
    assert "    ⚠ conservação local falha: Σ inputs = 73000000 ≠ value = 78000000 (cents)" in lines
    root_line = next(i for i, line in enumerate(lines) if line.startswith("[1] "))
    assert root_line > 0, "bloco anômalo deve vir antes da raiz limpa"


def test_needs_review_and_range_check_flagged_as_anomalies():
    tree = _clean_tree()
    tree["inputs"][0]["needs_review"] = True
    tree["range_check"] = "out_of_range"
    rendered = render_lineage_linear(tree)
    assert "    ⚠ needs_review=true" in rendered.splitlines()
    assert "    ⚠ range_check=out_of_range" in rendered.splitlines()


def test_dangling_node_renders_reason_inline():
    tree = _clean_tree()
    tree["inputs"][1] = {
        "node_type": "dangling",
        "stage": "E4",
        "artifact_key": "despesas",
        "field": "total",
        "reason": "artifact inexistente: stage='E4' key='despesas'",
    }
    rendered = render_lineage_linear(tree)
    assert (
        "[3] E4/despesas :: total | ⚠ dangling: artifact inexistente: stage='E4' key='despesas'"
        in rendered.splitlines()
    )


def test_render_is_deterministic():
    tree = _clean_tree()
    tree["inputs"][0]["value"] = "780000.00"
    assert render_lineage_linear(tree) == render_lineage_linear(tree)


def test_token_budget_omits_clean_blocks_but_keeps_anomalies():
    many_leaves = [_leaf(f"agg.item[{i:03d}].valor", 1.0) for i in range(120)]
    bad = _node("agg.total", "999.00", many_leaves)  # Σ = 120.00 ≠ 999.00
    tree = _node("root.total", "999.00", [bad], edge="formula")
    rendered = render_lineage_linear(tree, token_budget=200)
    assert len(rendered) <= 200 * 4 + 120
    assert "⚠ conservação local falha" in rendered
    assert "blocos omitidos, token_budget=200" in rendered.splitlines()[-1]


def test_full_anomalous_tree_fits_default_budget():
    many_leaves = [_leaf(f"agg.item[{i:02d}].valor", float(i)) for i in range(30)]
    bad = _node("agg.total", "9.00", many_leaves)
    rendered = render_lineage_linear(bad, token_budget=DEFAULT_TOKEN_BUDGET)
    assert len(rendered) <= DEFAULT_TOKEN_BUDGET * 4
