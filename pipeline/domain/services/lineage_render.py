"""Render textual da árvore de lineage (ADR-281 · A24.l5).

Puro/stateless; consumido por ``dev/explain_number.py`` e reusável na
fase MCP (ADR-281). Renderer LLM linearizado é F7.
"""

from __future__ import annotations

from pipeline.domain.services.lineage_resolver import LineageNode


def render_lineage_tree(node: LineageNode) -> str:
    return "\n".join(_render_lines(node, depth=0))


def _render_lines(node: LineageNode, depth: int) -> list[str]:
    indent = "  " * depth
    lines = [f"{indent}{line}" for line in _node_summary(node)]
    for child in node.get("inputs", []):
        lines.extend(_render_lines(child, depth + 1))
    return lines


def _node_summary(node: LineageNode) -> list[str]:
    location = f"{node['stage']}/{node['artifact_key']} :: {node['field']}"
    if node["node_type"] == "dangling":
        return [f"✗ {location} — dangling: {node['reason']}"]
    if node["node_type"] == "no_lineage":
        return [f"• {location} = {node['value']} (folha sem _lineage)"]
    rule = node.get("rule_ref") or {}
    return [
        f"{location} = {node['value']} ({node['label']})",
        f"  ↳ {node['transform']} [{node['edge_type']}] · "
        f"{rule.get('ref', '?')} ({rule.get('adr', '?')})",
    ]
