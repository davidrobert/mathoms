"""Goldens do ``lineage_diff`` (ADR-281 · A25.l4 F7): nós mudados,
``first_divergent_leaf`` e propagação anotada — tudo determinístico."""

from __future__ import annotations

import copy

from pipeline.domain.services.lineage_diff import lineage_diff

_STAGE = "E5"
_KEY = "analise_financeira"


def _leaf(field: str, value) -> dict:
    return {
        "node_type": "no_lineage",
        "stage": _STAGE,
        "artifact_key": _KEY,
        "field": field,
        "value": value,
    }


def _node(field: str, value: str, children: list[dict], *, edge="aggregation") -> dict:
    return {
        "node_type": "lineage",
        "stage": _STAGE,
        "artifact_key": _KEY,
        "field": field,
        "value": value,
        "label": field,
        "transform": f"t {field}",
        "edge_type": edge,
        "rule_ref": {"ref": "m:Q.calc", "adr": "ADR-145"},
        "inputs": children,
    }


def _tree() -> dict:
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


def _by_field(diff: dict) -> dict[str, dict]:
    return {c["node_id"]["field"]: c for c in diff["changed_nodes"]}


def test_identical_trees_have_no_changes():
    diff = lineage_diff(_tree(), _tree())
    assert diff["changed_nodes"] == []
    assert diff["first_divergent_leaf"] is None


def _leaf_delta_diff() -> dict:
    """Delta na folha composicao[a] propagado por bruto e liquido."""
    tree_b = _tree()
    tree_b["inputs"][0]["inputs"][0]["value"] = 650000.0
    tree_b["inputs"][0]["value"] = "780000.00"
    tree_b["value"] = "630000.00"
    return lineage_diff(_tree(), tree_b)


def test_leaf_delta_annotates_propagation_chain():
    changed = _by_field(_leaf_delta_diff())
    assert set(changed) == {
        "patrimonio.liquido",
        "patrimonio.bruto",
        "patrimonio.composicao[a].valor",
    }
    leaf = changed["patrimonio.composicao[a].valor"]
    assert leaf["kinds"] == ["value_changed"]
    assert leaf["origin"] == "local"
    bruto = changed["patrimonio.bruto"]
    assert bruto["origin"] == "propagated"
    assert [p["field"] for p in bruto["propagated_from"]] == ["patrimonio.composicao[a].valor"]
    liquido = changed["patrimonio.liquido"]
    assert [p["field"] for p in liquido["propagated_from"]] == ["patrimonio.bruto"]


def test_leaf_delta_first_divergent_leaf_is_the_leaf():
    assert _leaf_delta_diff()["first_divergent_leaf"] == {
        "stage": _STAGE,
        "artifact_key": _KEY,
        "field": "patrimonio.composicao[a].valor",
    }


def test_values_compare_in_cents_not_string():
    tree_b = _tree()
    tree_b["inputs"][1]["value"] = 150000.0000001  # mesmo valor em cents
    assert lineage_diff(_tree(), tree_b)["changed_nodes"] == []


def test_input_removed_is_inputs_changed_local():
    tree_b = _tree()
    del tree_b["inputs"][0]["inputs"][1]
    diff = lineage_diff(_tree(), tree_b)
    changed = _by_field(diff)
    assert changed["patrimonio.bruto"]["kinds"] == ["inputs_changed"]
    assert changed["patrimonio.composicao[b].valor"]["kinds"] == ["only_in_a"]
    # b-only/a-only nó é divergência local mais profunda.
    assert diff["first_divergent_leaf"]["field"] == "patrimonio.composicao[b].valor"


def test_rule_ref_swap_detected():
    tree_b = _tree()
    tree_b["inputs"][0]["rule_ref"] = {"ref": "m:Outro.calc", "adr": "ADR-218"}
    changed = _by_field(lineage_diff(_tree(), tree_b))
    assert changed["patrimonio.bruto"]["kinds"] == ["rule_ref_changed"]
    assert changed["patrimonio.bruto"]["origin"] == "local"


def test_node_type_change_detected():
    tree_b = _tree()
    tree_b["inputs"][0] = {
        "node_type": "dangling",
        "stage": _STAGE,
        "artifact_key": _KEY,
        "field": "patrimonio.bruto",
        "reason": "ciclo",
    }
    changed = _by_field(lineage_diff(_tree(), tree_b))
    assert "node_type_changed" in changed["patrimonio.bruto"]["kinds"]


def test_diff_is_pure_no_mutation():
    tree_a, tree_b = _tree(), _tree()
    tree_b["value"] = "0.00"
    snapshot_a, snapshot_b = copy.deepcopy(tree_a), copy.deepcopy(tree_b)
    lineage_diff(tree_a, tree_b)
    assert tree_a == snapshot_a and tree_b == snapshot_b
