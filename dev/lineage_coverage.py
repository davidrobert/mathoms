#!/usr/bin/env python3
"""Cobertura do grafo de lineage (ADR-281 · A27.l2): raízes monetárias do E5 com nó ÷ raízes monetárias do E5.

O denominador sai do **payload publicado**, nunca do ``lineage_registry``: derivá-lo do
registro devolve 100% por construção — o vício que esta medida existe para matar (raiz
nova no E5 sem entrada no registro não movia métrica nenhuma, nem o gate, nem a accuracy).
O discriminante de "raiz que deve ter rastro" é ``golden_diff.is_monetary``
(monetário-por-default, ADR-090). O que o qualifica é ser **independente do
``lineage_registry``** — é isso que mantém numerador e denominador independentes — e já ser
o classificador de dot-path que o substrato de golden usa (``golden_diff``, snapshot do
view-model), então reusá-lo não cria uma segunda noção de "monetário" para o mesmo payload.

Raiz em prosa/metadado (``alertas``, ``data_analise``, ``tarefas``) fica fora do denominador
porque não publica dinheiro. Medir contra as 38 raízes declaradas no schema
dava teto inalcançável, e KR que não pode chegar a 100% é KR que ninguém persegue.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dev.golden_diff import is_monetary  # noqa: E402

# O bloco de rastro não entra no denominador: uma raiz não pode ser evidência da
# própria proveniência. Declarado aqui por princípio — hoje `_lineage` serializa
# valor como string e não cairia no predicado de qualquer forma.
LINEAGE_BLOCK = "_lineage"


def _children(obj: Any, path: str) -> list[tuple[str, Any]]:
    if isinstance(obj, dict):
        return [(f"{path}.{k}" if path else k, v) for k, v in obj.items()]
    if isinstance(obj, list):
        return [(f"{path}[{i}]", v) for i, v in enumerate(obj)]
    return []


def _is_monetary_leaf(obj: Any, path: str) -> bool:
    return isinstance(obj, (int, float)) and not isinstance(obj, bool) and is_monetary(path)


def monetary_leaf_paths(payload: Any, path: str = "") -> set[str]:
    """Dot-paths das folhas monetárias do payload (recursivo em dict e list)."""
    children = _children(payload, path)
    if not children:
        return {path} if _is_monetary_leaf(payload, path) else set()
    found: set[str] = set()
    for child_path, value in children:
        found |= monetary_leaf_paths(value, child_path)
    return found


def _root_of(path: str) -> str:
    return path.split(".", 1)[0].split("[", 1)[0]


def payload_monetary_roots(payload: dict) -> frozenset[str]:
    """Denominador: raízes de topo que publicam ≥1 folha monetária."""
    roots = {_root_of(p) for p in monetary_leaf_paths(payload)}
    return frozenset(roots - {LINEAGE_BLOCK})


def lineage_covered_roots(payload: dict) -> frozenset[str]:
    """Numerador: raízes com ≥1 nó declarado em ``_lineage.fields``."""
    fields = payload.get(LINEAGE_BLOCK, {}).get("fields", {})
    return frozenset(_root_of(f) for f in fields)


@dataclass(frozen=True)
class LineageCoverage:
    """Cobertura medida sobre um payload E5 concreto."""

    monetary_roots: frozenset[str]
    covered_roots: frozenset[str]

    @property
    def uncovered_roots(self) -> frozenset[str]:
        return self.monetary_roots - self.covered_roots

    @property
    def ratio(self) -> float:
        if not self.monetary_roots:
            return 0.0
        return len(self.monetary_roots & self.covered_roots) / len(self.monetary_roots)

    def format_summary(self) -> str:
        hit = len(self.monetary_roots & self.covered_roots)
        return f"{hit}/{len(self.monetary_roots)} raízes monetárias com rastro ({self.ratio:.1%})"


def measure_coverage(payload: dict) -> LineageCoverage:
    """Cobertura de lineage do payload E5 publicado."""
    return LineageCoverage(
        monetary_roots=payload_monetary_roots(payload),
        covered_roots=lineage_covered_roots(payload),
    )
