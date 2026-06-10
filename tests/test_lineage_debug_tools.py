"""Tools de debug de lineage (ADR-281 · A25.l4 F7): whitelist, cap de 6
iterações, audit trail e leitura read-only sobre InMemoryArtifactStore."""

from __future__ import annotations

import pytest

from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.domain.lineage_registry import LINEAGE_RULE_REFS
from pipeline.domain.services.lineage_debug_tools import (
    MAX_EXPAND_ITERATIONS,
    LineageDebugTools,
    lineage_debug_whitelist,
)

_PAYLOAD = {
    "patrimonio": {
        "bruto": 730000.0,
        "dividas": 150000.0,
        "liquido": 580000.0,
        "composicao": [
            {"categoria": "a", "valor": 600000.0},
            {"categoria": "b", "valor": 130000.0},
        ],
    },
    "_lineage": {
        "lineage_version": "1.0",
        "fields": {
            "patrimonio.liquido": {
                "value": "580000.00",
                "label": "Patrimônio líquido",
                "transform": "bruto − dividas",
                "rule_ref": dict(LINEAGE_RULE_REFS["patrimonio.liquido"]),
                "edge_type": "formula",
                "member_hashes": [],
                "inputs": [
                    {
                        "stage": "E5",
                        "artifact_key": "analise_financeira",
                        "field": "patrimonio.bruto",
                    },
                    {
                        "stage": "E5",
                        "artifact_key": "analise_financeira",
                        "field": "patrimonio.dividas",
                    },
                ],
            },
            "patrimonio.bruto": {
                "value": "730000.00",
                "label": "Patrimônio bruto",
                "transform": "soma das categorias",
                "rule_ref": dict(LINEAGE_RULE_REFS["patrimonio.bruto"]),
                "edge_type": "aggregation",
                "member_hashes": [],
                "inputs": [
                    {
                        "stage": "E5",
                        "artifact_key": "analise_financeira",
                        "field": "patrimonio.composicao[a].valor",
                    },
                    {
                        "stage": "E5",
                        "artifact_key": "analise_financeira",
                        "field": "patrimonio.composicao[b].valor",
                    },
                ],
            },
        },
    },
}


@pytest.fixture
def tools() -> LineageDebugTools:
    store = InMemoryArtifactStore()
    store.seed("E5", "analise_financeira", _PAYLOAD)
    return LineageDebugTools(store=store, whitelist=lineage_debug_whitelist())


def test_whitelist_is_derived_from_registry():
    assert lineage_debug_whitelist() == frozenset(LINEAGE_RULE_REFS)


def test_explain_number_renders_whitelisted_field(tools):
    result = tools.explain_number("patrimonio.liquido")
    assert result["found"] is True
    assert "[1] patrimonio.liquido = 580000.00" in result["rendered"]


def test_explain_number_rejects_non_whitelisted_field(tools):
    result = tools.explain_number("patrimonio.dividas")
    assert result == {"found": False, "reason": "field_not_whitelisted"}


def test_explain_number_depth_truncates_subtree(tools):
    shallow = tools.explain_number("patrimonio.liquido", depth=1)
    deep = tools.explain_number("patrimonio.liquido", depth=3)
    # depth=1 poda os netos: bruto vira nó sem inputs (1 nó, sem colapso);
    # depth=3 alcança as folhas e a subárvore limpa colapsa com contagem real.
    assert "(3 nós, sem anomalia)" not in shallow["rendered"]
    assert "(3 nós, sem anomalia)" in deep["rendered"]


def test_expand_node_resolves_arbitrary_seen_node(tools):
    result = tools.expand_node("E5", "analise_financeira", "patrimonio.bruto")
    assert result["found"] is True
    assert "composicao[a]" in result["rendered"]


def test_expand_node_dangling_is_not_found(tools):
    result = tools.expand_node("E4", "despesas", "total")
    assert result["found"] is False
    assert "dangling" in result["reason"]


def test_trace_source_returns_leaves(tools):
    result = tools.trace_source("patrimonio.bruto")
    assert result["found"] is True
    assert [leaf["field"] for leaf in result["leaves"]] == [
        "patrimonio.composicao[a].valor",
        "patrimonio.composicao[b].valor",
    ]
    assert all(leaf["node_type"] == "no_lineage" for leaf in result["leaves"])


def test_cap_max_expand_iterations(tools):
    for _ in range(MAX_EXPAND_ITERATIONS):
        assert tools.trace_source("patrimonio.bruto")["found"] is True
    over_cap = tools.trace_source("patrimonio.bruto")
    assert over_cap == {"found": False, "reason": "max_iterations_exceeded"}
    assert tools.iterations_count == MAX_EXPAND_ITERATIONS + 1


def test_audit_trace_records_every_call(tools):
    tools.explain_number("patrimonio.liquido")
    tools.explain_number("nope")
    trace = tools.to_trace_dicts()
    assert [t["tool"] for t in trace] == ["explain_number", "explain_number"]
    assert trace[0]["result_summary"] == {"found": True, "reason": None}
    assert trace[1]["result_summary"] == {"found": False, "reason": "field_not_whitelisted"}
    assert [t["iter"] for t in trace] == [1, 2]
