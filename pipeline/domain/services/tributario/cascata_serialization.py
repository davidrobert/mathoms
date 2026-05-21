"""Serializa ``CascataOutput`` para dict JSON-friendly (ADR-236 §D4)."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any

from pipeline.domain.services.tributario.cascata_calculator import CascataOutput


def cascata_to_dict(output: CascataOutput) -> dict[str, object]:
    """Narrador consome via ``M['tributario']['cascata']`` (ADR-236 §D4)."""
    return _normalize(asdict(output))


def _normalize(node: Any) -> Any:
    if isinstance(node, dict):
        if _is_money_shape(node):
            return _node_to_float(node)
        return {k: _normalize(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_normalize(v) for v in node]
    if isinstance(node, Decimal):
        return float(node)
    return node


def _is_money_shape(node: dict) -> bool:
    return set(node.keys()) == {"amount", "currency"} and isinstance(
        node.get("amount"), (Decimal, int, str)
    )


def _node_to_float(node: dict) -> float:
    return float(Decimal(str(node["amount"])))
