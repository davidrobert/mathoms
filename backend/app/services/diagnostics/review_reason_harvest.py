"""Colheita de razão de review do `detail` de um stage, em QUALQUER posição do
artefato ([[ADR-411]] D2).

Produtor único do caminhamento: o gate de cobertura mede com ESTA função. Um
predicado que caminhasse por conta própria leria só a coleção de topo e
certificaria o meio-fix — no run `d0f6260a`, 2 das 4 razões do
`consolidate_baseline` estavam em `imoveis_consolidados[].review_reasons`.
"""

from __future__ import annotations

from typing import Any

from backend.app.core.logging import get_logger

logger = get_logger("pipeline.diagnostics")

REASON_COLLECTION_KEY = "review_reasons"

# Teto de colheita: razão é diagnóstico, não dump. Produtor que emita razão por
# item sobre corpus grande inflaria a passagem inteira. O corte é LOGADO — cap
# silencioso é o que faz um gate de cobertura ler "cobri tudo" sem ter coberto.
_HARVEST_CAP = 1000


def _child_path(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _reasons_in(collection: Any, locator: str) -> list[dict[str, Any]]:
    """Razões da coleção, carimbadas com o caminho onde foram achadas.

    Copia o dict: o `detail` é o payload que o stage vai persistir como
    artefato, e carimbar in-place o contaminaria com campo que o schema do
    produtor não declara.
    """
    if not isinstance(collection, list):
        return []
    return [
        {**item, "locator": locator}
        for item in collection
        if isinstance(item, dict) and item.get("code")
    ]


def _walk(node: Any, path: str, out: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        _walk_dict(node, path, out)
    elif isinstance(node, list):
        for item in node:
            _walk(item, f"{path}[]", out)


def _walk_dict(node: dict, path: str, out: list[dict[str, Any]]) -> None:
    """Coleção de razões vira colheita; qualquer outra chave segue sendo caminhada."""
    for key, value in node.items():
        child = _child_path(path, key)
        if key == REASON_COLLECTION_KEY:
            out.extend(_reasons_in(value, child))
        else:
            _walk(value, child, out)


def _capped(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(rows) <= _HARVEST_CAP:
        return rows
    logger.error(
        "colheita de review_reasons truncada — razões acima do teto ficaram fora",
        extra={
            "event": "mathoms.pipeline.review_reason_harvest_capped",
            "harvested": _HARVEST_CAP,
            "dropped": len(rows) - _HARVEST_CAP,
        },
    )
    return rows[:_HARVEST_CAP]


def harvest_review_reasons(detail: Any) -> list[dict[str, Any]]:
    """Toda razão do `detail`, onde quer que esteja, com o locator da coleção."""
    if not isinstance(detail, (dict, list)):
        return []
    out: list[dict[str, Any]] = []
    _walk(detail, "", out)
    return _capped(out)


__all__ = ["REASON_COLLECTION_KEY", "harvest_review_reasons"]
