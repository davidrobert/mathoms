"""Renderer LLM-linearizado da árvore de lineage (ADR-281 · A25.l4 F7) — distinto do renderer humano (``lineage_render.py``): linha por nó com id global ``[N]``, inputs como ``#N``, anomaly-first e colapso de subárvore limpa, projetado p/ ~1.5k tokens de contexto de debug; puro/stateless, determinismo por construção (BFS + sort estável)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from pipeline.domain.services.lineage_resolver import LineageNode

DEFAULT_TOKEN_BUDGET = 1500
# Heurística conservadora de tokens p/ texto técnico pt-BR (~4 chars/token).
_CHARS_PER_TOKEN = 4
_RANGE_CHECK_OK = (None, "ok")


@dataclass
class _IndexedNode:
    node_id: int
    node: LineageNode
    children: list["_IndexedNode"] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    subtree_size: int = 1
    subtree_clean: bool = True


def render_lineage_linear(tree: LineageNode, *, token_budget: int = DEFAULT_TOKEN_BUDGET) -> str:
    """Lineariza em 2 passadas (BFS coleta → emite ⚠ primeiro), ordenação ``(tem_anomalia desc, node_id asc)``; subárvore inteiramente limpa colapsa em 1 linha ``✓ (K nós, sem anomalia)``."""
    root = _index_bfs(tree)
    blocks = _collect_blocks(root, is_root=True, root_node=tree)
    blocks.sort(key=lambda b: (not b[0], b[1]))
    return _emit_within_budget(blocks, token_budget)


def _index_bfs(tree: LineageNode) -> _IndexedNode:
    root = _IndexedNode(node_id=1, node=tree)
    queue = [root]
    next_id = 2
    while queue:
        indexed = queue.pop(0)
        for child in indexed.node.get("inputs", []):
            child_indexed = _IndexedNode(node_id=next_id, node=child)
            next_id += 1
            indexed.children.append(child_indexed)
            queue.append(child_indexed)
    _annotate_bottom_up(root)
    return root


def _annotate_bottom_up(indexed: _IndexedNode) -> None:
    for child in indexed.children:
        _annotate_bottom_up(child)
    indexed.anomalies = _node_anomalies(indexed.node, indexed.children)
    indexed.subtree_size = 1 + sum(c.subtree_size for c in indexed.children)
    indexed.subtree_clean = not indexed.anomalies and all(c.subtree_clean for c in indexed.children)


def _node_anomalies(node: LineageNode, children: list[_IndexedNode]) -> list[str]:
    anomalies: list[str] = []
    if node["node_type"] == "dangling":
        anomalies.append(f"dangling: {node['reason']}")
    if node.get("needs_review") is True:
        anomalies.append("needs_review=true")
    range_check = node.get("range_check")
    if range_check not in _RANGE_CHECK_OK:
        anomalies.append(f"range_check={range_check}")
    conservation = _conservation_gap(node, children)
    if conservation is not None:
        anomalies.append(conservation)
    return anomalies


def _conservation_gap(node: LineageNode, children: list[_IndexedNode]) -> str | None:
    """Σ inputs ≠ value em cents int — só p/ aggregation com filhos numéricos."""
    if node["node_type"] != "lineage" or node.get("edge_type") != "aggregation" or not children:
        return None
    value_cents = _cents(node.get("value"))
    child_cents = [_cents(c.node.get("value")) for c in children]
    if value_cents is None or any(c is None for c in child_cents):
        return None
    total = sum(child_cents)  # type: ignore[arg-type]
    if total == value_cents:
        return None
    return f"conservação local falha: Σ inputs = {total} ≠ value = {value_cents} (cents)"


def _cents(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return None


def _collect_blocks(
    indexed: _IndexedNode, *, is_root: bool, root_node: LineageNode
) -> list[tuple[bool, int, list[str]]]:
    """Blocos ``(tem_anomalia, node_id, linhas)`` — colapso de subárvore limpa não-raiz."""
    if not is_root and indexed.subtree_clean and indexed.subtree_size > 1:
        return [(False, indexed.node_id, [_collapsed_line(indexed)])]
    blocks = [(bool(indexed.anomalies), indexed.node_id, _node_block(indexed, root_node))]
    for child in indexed.children:
        blocks.extend(_collect_blocks(child, is_root=False, root_node=root_node))
    return blocks


def _collapsed_line(indexed: _IndexedNode) -> str:
    location = indexed.node["field"]
    value = indexed.node.get("value")
    prefix = f"[{indexed.node_id}] {location}"
    if value is not None:
        prefix += f" = {value}"
    return f"{prefix} ✓ ({indexed.subtree_size} nós, sem anomalia)"


def _node_block(indexed: _IndexedNode, root_node: LineageNode) -> list[str]:
    node = indexed.node
    location = _location(node, root_node)
    if node["node_type"] == "dangling":
        lines = [f"[{indexed.node_id}] {location} | ⚠ dangling: {node['reason']}"]
        return lines + [f"    ⚠ {a}" for a in indexed.anomalies if not a.startswith("dangling:")]
    if node["node_type"] == "no_lineage":
        source = f"{node['stage']}/{node['artifact_key']}"
        lines = [f"[{indexed.node_id}] {location} = {node.get('value')} | folha: {source}"]
        return lines + [f"    ⚠ {a}" for a in indexed.anomalies]
    return _lineage_block(indexed, location)


def _lineage_block(indexed: _IndexedNode, location: str) -> list[str]:
    node = indexed.node
    lines = [
        f"[{indexed.node_id}] {location} = {node.get('value')} | {node.get('label')} | "
        f"{node.get('transform')} [{node.get('edge_type')}]"
    ]
    if indexed.children:
        refs = " ".join(f"#{c.node_id}" for c in indexed.children)
        lines.append(f"    inputs: {refs}")
    rule = node.get("rule_ref") or {}
    if rule:
        lines.append(f"    rule: {rule.get('ref', '?')} ({rule.get('adr', '?')})")
    lines.extend(f"    ⚠ {a}" for a in indexed.anomalies)
    return lines


def _location(node: LineageNode, root_node: LineageNode) -> str:
    same_artifact = (node["stage"], node["artifact_key"]) == (
        root_node["stage"],
        root_node["artifact_key"],
    )
    if same_artifact:
        return node["field"]
    return f"{node['stage']}/{node['artifact_key']} :: {node['field']}"


def _emit_within_budget(blocks: list[tuple[bool, int, list[str]]], token_budget: int) -> str:
    char_budget = token_budget * _CHARS_PER_TOKEN
    lines: list[str] = []
    used = 0
    omitted = 0
    for _, _, block_lines in blocks:
        block_chars = sum(len(line) + 1 for line in block_lines)
        if used + block_chars > char_budget and lines:
            omitted += 1
            continue
        lines.extend(block_lines)
        used += block_chars
    if omitted:
        lines.append(f"… ({omitted} blocos omitidos, token_budget={token_budget})")
    return "\n".join(lines)
