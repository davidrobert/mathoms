"""Tools de debug de lineage p/ loop LLM (ADR-281 · A25.l4 F7): funções de domínio puras sobre ``ReadableArtifactStore`` — superfície read-only, sem backend/MCP (deferido por ADR-281) — com whitelist de ``field`` derivada do ``lineage_registry``, cap duro ``max_expand_iterations=6`` e audit trail serializável p/ ``_meta.tool_trace`` (padrão PlannerDrillDown)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pipeline.artifact_store import ReadableArtifactStore
from pipeline.domain.lineage_registry import LINEAGE_RULE_REFS
from pipeline.domain.services.lineage_render_llm import render_lineage_linear
from pipeline.domain.services.lineage_resolver import LineageNode, LineageResolver

MAX_EXPAND_ITERATIONS = 6
_DEFAULT_DEPTH = 2


def lineage_debug_whitelist() -> frozenset[str]:
    """Campos com regra registrada — únicos entrypoints de explain/trace."""
    return frozenset(LINEAGE_RULE_REFS)


@dataclass
class LineageDebugTools:
    """Provider das 3 tools — resolver read-only + cap + audit trail."""

    store: ReadableArtifactStore
    whitelist: frozenset[str]
    stage: str = "E5"
    artifact_key: str = "analise_financeira"
    max_expand_iterations: int = MAX_EXPAND_ITERATIONS

    trace: list[dict] = field(default_factory=list, init=False)
    _iter: int = field(default=0, init=False)

    def explain_number(self, field_path: str, depth: int = _DEFAULT_DEPTH) -> dict:
        """Render linear da árvore do campo (whitelisted), truncada em ``depth``."""
        return self._invoke(
            "explain_number",
            {"field": field_path, "depth": depth},
            lambda: self._explain(field_path, depth),
        )

    def expand_node(self, stage: str, artifact_key: str, field_path: str) -> dict:
        """Expande 1 nó arbitrário já visto na árvore (read-only, 2 níveis)."""
        return self._invoke(
            "expand_node",
            {"stage": stage, "artifact_key": artifact_key, "field": field_path},
            lambda: self._expand(stage, artifact_key, field_path),
        )

    def trace_source(self, field_path: str) -> dict:
        """Folhas (fontes) da árvore do campo whitelisted."""
        return self._invoke(
            "trace_source",
            {"field": field_path},
            lambda: self._trace(field_path),
        )

    @property
    def iterations_count(self) -> int:
        return self._iter

    def to_trace_dicts(self) -> list[dict]:
        return list(self.trace)

    def _invoke(self, tool: str, tool_input: dict, resolver: Callable[[], dict]) -> dict:
        self._iter += 1
        if self._iter > self.max_expand_iterations:
            result = {"found": False, "reason": "max_iterations_exceeded"}
        else:
            result = resolver()
        self.trace.append(
            {
                "iter": self._iter,
                "tool": tool,
                "input": tool_input,
                "result_summary": {"found": result["found"], "reason": result.get("reason")},
            }
        )
        return result

    def _explain(self, field_path: str, depth: int) -> dict:
        if field_path not in self.whitelist:
            return {"found": False, "reason": "field_not_whitelisted"}
        tree = self._resolve(self.stage, self.artifact_key, field_path)
        pruned = _prune_depth(tree, max(depth, 1))
        return {"found": True, "rendered": render_lineage_linear(pruned)}

    def _expand(self, stage: str, artifact_key: str, field_path: str) -> dict:
        tree = self._resolve(stage, artifact_key, field_path)
        if tree["node_type"] == "dangling":
            return {"found": False, "reason": f"dangling: {tree['reason']}"}
        return {"found": True, "rendered": render_lineage_linear(_prune_depth(tree, 2))}

    def _trace(self, field_path: str) -> dict:
        if field_path not in self.whitelist:
            return {"found": False, "reason": "field_not_whitelisted"}
        tree = self._resolve(self.stage, self.artifact_key, field_path)
        leaves = _collect_leaves(tree)
        return {"found": True, "leaves": leaves}

    def _resolve(self, stage: str, artifact_key: str, field_path: str) -> LineageNode:
        return LineageResolver(self.store).resolve(stage, artifact_key, field_path)


def _prune_depth(node: LineageNode, depth: int) -> LineageNode:
    pruned: dict[str, Any] = {k: v for k, v in node.items() if k != "inputs"}
    children = node.get("inputs", [])
    if not children:
        return pruned
    if depth <= 0:
        pruned["truncated"] = True
        return pruned
    pruned["inputs"] = [_prune_depth(c, depth - 1) for c in children]
    return pruned


def _collect_leaves(node: LineageNode) -> list[dict]:
    children = node.get("inputs", [])
    if not children:
        return [
            {
                "stage": node["stage"],
                "artifact_key": node["artifact_key"],
                "field": node["field"],
                "node_type": node["node_type"],
                "value": node.get("value"),
            }
        ]
    leaves: list[dict] = []
    for child in children:
        leaves.extend(_collect_leaves(child))
    return leaves
