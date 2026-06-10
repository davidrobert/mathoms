"""Diff determinístico entre duas árvores de lineage (ADR-281 · A25.l4 F7): puro/stateless, nós mudados + ``first_divergent_leaf`` (origem mais profunda da divergência) + propagação anotada (``origin`` local vs ``propagated``); valores numéricos comparam em cents int (ADR-090), demais por igualdade."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, TypedDict

from pipeline.domain.services.lineage_resolver import LineageNode

NodeKey = tuple[str, str, str]


class NodeRef(TypedDict):
    stage: str
    artifact_key: str
    field: str


class ChangedNode(TypedDict):
    node_id: NodeRef
    kinds: list[str]
    value_a: Any
    value_b: Any
    origin: str
    propagated_from: list[NodeRef]


class LineageDiffResult(TypedDict):
    changed_nodes: list[ChangedNode]
    first_divergent_leaf: NodeRef | None


@dataclass(frozen=True)
class _IndexEntry:
    node: LineageNode
    depth: int
    order: int
    input_keys: tuple[NodeKey, ...]


@dataclass
class _Change:
    kinds: list[str]
    value_a: Any
    value_b: Any
    depth: int
    order: tuple[int, int]
    input_keys: tuple[NodeKey, ...]
    origin: str = "local"
    propagated_from: list[NodeKey] | None = None


def lineage_diff(tree_a: LineageNode, tree_b: LineageNode) -> LineageDiffResult:
    """``first_divergent_leaf`` = nó mudado de ``origin == "local"`` mais profundo (desempate por ordem DFS preorder de A, depois B) — a folha onde a divergência nasce antes de propagar pelos agregados."""
    index_a = _index(tree_a)
    index_b = _index(tree_b)
    changed = _changed_nodes(index_a, index_b)
    _annotate_propagation(changed)
    return {
        "changed_nodes": [_serialize(key, change) for key, change in changed.items()],
        "first_divergent_leaf": _first_divergent_leaf(changed),
    }


def _index(tree: LineageNode) -> dict[NodeKey, _IndexEntry]:
    entries: dict[NodeKey, _IndexEntry] = {}
    _walk(tree, depth=0, counter=[0], entries=entries)
    return entries


def _walk(
    node: LineageNode, *, depth: int, counter: list[int], entries: dict[NodeKey, _IndexEntry]
) -> None:
    key = _node_key(node)
    if key in entries:
        return
    children = node.get("inputs", [])
    entries[key] = _IndexEntry(
        node=node,
        depth=depth,
        order=counter[0],
        input_keys=tuple(_node_key(c) for c in children),
    )
    counter[0] += 1
    for child in children:
        _walk(child, depth=depth + 1, counter=counter, entries=entries)


def _node_key(node: LineageNode) -> NodeKey:
    return (node["stage"], node["artifact_key"], node["field"])


def _changed_nodes(
    index_a: dict[NodeKey, _IndexEntry], index_b: dict[NodeKey, _IndexEntry]
) -> dict[NodeKey, _Change]:
    changed: dict[NodeKey, _Change] = {}
    ordered_keys = list(index_a) + [k for k in index_b if k not in index_a]
    for key in ordered_keys:
        change = _change_for(index_a.get(key), index_b.get(key))
        if change is not None:
            changed[key] = change
    return changed


def _change_for(entry_a: _IndexEntry | None, entry_b: _IndexEntry | None) -> _Change | None:
    kinds = _compare(entry_a, entry_b)
    if not kinds:
        return None
    anchor = entry_a or entry_b
    assert anchor is not None
    return _Change(
        kinds=kinds,
        value_a=entry_a.node.get("value") if entry_a else None,
        value_b=entry_b.node.get("value") if entry_b else None,
        depth=anchor.depth,
        order=(0 if entry_a else 1, anchor.order),
        input_keys=_union_inputs(entry_a, entry_b),
    )


def _compare(entry_a: _IndexEntry | None, entry_b: _IndexEntry | None) -> list[str]:
    if entry_a is None:
        return ["only_in_b"]
    if entry_b is None:
        return ["only_in_a"]
    kinds: list[str] = []
    node_a, node_b = entry_a.node, entry_b.node
    if node_a["node_type"] != node_b["node_type"]:
        kinds.append("node_type_changed")
    if _values_differ(node_a.get("value"), node_b.get("value")):
        kinds.append("value_changed")
    if node_a.get("rule_ref") != node_b.get("rule_ref"):
        kinds.append("rule_ref_changed")
    if entry_a.input_keys != entry_b.input_keys:
        kinds.append("inputs_changed")
    return kinds


def _values_differ(value_a: Any, value_b: Any) -> bool:
    cents_a, cents_b = _cents(value_a), _cents(value_b)
    if cents_a is not None and cents_b is not None:
        return cents_a != cents_b
    return value_a != value_b


def _cents(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return None


def _union_inputs(entry_a: _IndexEntry | None, entry_b: _IndexEntry | None) -> tuple[NodeKey, ...]:
    keys_a = entry_a.input_keys if entry_a else ()
    keys_b = entry_b.input_keys if entry_b else ()
    return tuple(dict.fromkeys((*keys_a, *keys_b)))


def _annotate_propagation(changed: dict[NodeKey, _Change]) -> None:
    for change in changed.values():
        propagated_from = [key for key in change.input_keys if key in changed]
        change.origin = "propagated" if propagated_from else "local"
        change.propagated_from = propagated_from


def _node_ref(key: NodeKey) -> NodeRef:
    return {"stage": key[0], "artifact_key": key[1], "field": key[2]}


def _serialize(key: NodeKey, change: _Change) -> ChangedNode:
    return {
        "node_id": _node_ref(key),
        "kinds": change.kinds,
        "value_a": change.value_a,
        "value_b": change.value_b,
        "origin": change.origin,
        "propagated_from": [_node_ref(k) for k in change.propagated_from or []],
    }


def _first_divergent_leaf(changed: dict[NodeKey, _Change]) -> NodeRef | None:
    candidates = [
        (-change.depth, change.order, key)
        for key, change in changed.items()
        if change.origin == "local"
    ]
    if not candidates:
        return None
    _, _, key = min(candidates)
    return _node_ref(key)
