"""Resolução forward de lineage field-level (ADR-279 · A24.l5).

Read-only sobre o protocol ``ArtifactStore``, stateless (ADR-111).
Referência irresolúvel vira nó ``dangling``; campo presente sem entrada
``_lineage`` vira nó ``no_lineage`` — nunca exceção.
"""

from __future__ import annotations

import re
from typing import Any

from pipeline.artifact_store import ReadableArtifactStore

LineageNode = dict[str, Any]

_MISSING = object()
_SEGMENT_RE = re.compile(r"^(?P<name>[^.\[\]]+)(?:\[(?P<selector>[^\]]+)\])?$")
# Chaves naturais para selecionar item de lista por valor (paridade com
# golden_diff._NATURAL_KEYS).
_NATURAL_KEYS = ("categoria", "property_id", "codigo_rfb", "code", "id", "nome", "key")


class LineageResolver:
    """Resolve ``(stage, artifact_key, field)`` na árvore de lineage."""

    def __init__(self, store: ReadableArtifactStore) -> None:
        self._store = store

    def resolve(self, stage: str, artifact_key: str, field: str) -> LineageNode:
        return self._resolve(stage, artifact_key, field, visited=frozenset())

    def _resolve(
        self, stage: str, key: str, field: str, visited: frozenset[tuple[str, str, str]]
    ) -> LineageNode:
        node_id = (stage, key, field)
        if node_id in visited:
            return _dangling(stage, key, field, reason=f"ciclo de lineage em {node_id!r}")
        payload = self._store.read(stage, key)
        if payload is None:
            return _dangling(
                stage, key, field, reason=f"artifact inexistente: stage={stage!r} key={key!r}"
            )
        return self._node_from_payload(payload, stage, key, field, visited | {node_id})

    def _node_from_payload(
        self,
        payload: dict,
        stage: str,
        key: str,
        field: str,
        visited: frozenset[tuple[str, str, str]],
    ) -> LineageNode:
        entry = _lineage_entry(payload, field)
        value = resolve_field_path(payload, field)
        if entry is None:
            if value is _MISSING:
                return _dangling(
                    stage, key, field, reason=f"campo inexistente no payload: {field!r}"
                )
            return _no_lineage(stage, key, field, value)
        children = [
            self._resolve(i["stage"], i["artifact_key"], i["field"], visited)
            for i in entry.get("inputs", [])
        ]
        return _lineage_node(stage, key, field, entry, children)


def resolve_field_path(payload: dict, field: str) -> Any:
    """Resolve dot-path com seletor ``[chave-natural|índice]``; ``_MISSING`` se irresolúvel."""
    current: Any = payload
    for segment in field.split("."):
        current = _step(current, segment)
        if current is _MISSING:
            return _MISSING
    return current


def is_missing(value: Any) -> bool:
    return value is _MISSING


def _step(current: Any, segment: str) -> Any:
    match = _SEGMENT_RE.match(segment)
    if match is None or not isinstance(current, dict) or match["name"] not in current:
        return _MISSING
    value = current[match["name"]]
    selector = match["selector"]
    return value if selector is None else _select_item(value, selector)


def _select_item(value: Any, selector: str) -> Any:
    if not isinstance(value, list):
        return _MISSING
    if selector.isdigit():
        return value[int(selector)] if int(selector) < len(value) else _MISSING
    for item in value:
        if isinstance(item, dict) and any(item.get(k) == selector for k in _NATURAL_KEYS):
            return item
    return _MISSING


def _lineage_entry(payload: dict, field: str) -> dict | None:
    fields = (payload.get("_lineage") or {}).get("fields") or {}
    return fields.get(field)


def _base_node(node_type: str, stage: str, key: str, field: str) -> LineageNode:
    return {"node_type": node_type, "stage": stage, "artifact_key": key, "field": field}


def _dangling(stage: str, key: str, field: str, *, reason: str) -> LineageNode:
    return {**_base_node("dangling", stage, key, field), "reason": reason}


def _no_lineage(stage: str, key: str, field: str, value: Any) -> LineageNode:
    return {**_base_node("no_lineage", stage, key, field), "value": value}


# Sinais de qualidade do entry propagados ao nó quando presentes (F7,
# ADR-281): o renderer LLM trata needs_review/range_check como anomalia.
_QUALITY_SIGNAL_KEYS = ("needs_review", "range_check", "signals")


def _lineage_node(
    stage: str, key: str, field: str, entry: dict, children: list[LineageNode]
) -> LineageNode:
    node = {
        **_base_node("lineage", stage, key, field),
        "value": entry.get("value"),
        "label": entry.get("label"),
        "transform": entry.get("transform"),
        "edge_type": entry.get("edge_type"),
        "rule_ref": entry.get("rule_ref"),
        "inputs": children,
    }
    for signal_key in _QUALITY_SIGNAL_KEYS:
        if signal_key in entry:
            node[signal_key] = entry[signal_key]
    return node
