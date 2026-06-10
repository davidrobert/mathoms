"""Helpers compartilhados dos blocos ``_lineage`` field-level E5 (ADR-279 · A24.l6): ``value`` string decimal 2 casas derivada do float serializado (nunca recálculo paralelo, escapa do ``to_cents``/manifesto do ``golden_diff``); ``inputs`` com sort canônico ``(stage, artifact_key, field)`` — load-bearing p/ byte-identidade e diff posicional."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

LINEAGE_VERSION = "1.0"
E5_STAGE = "E5"
E5_ANALISE_KEY = "analise_financeira"

# Payloads JSON wire-shaped — shape canônico em
# config/schemas/e5_analysis.schema.json (`_lineage`).
LineageBlock = dict[str, Any]
LineageField = dict[str, Any]


def money_str(value: float) -> str:
    return f"{Decimal(str(value)):.2f}"


def e5_input_ref(field: str) -> dict[str, str]:
    return {"stage": E5_STAGE, "artifact_key": E5_ANALISE_KEY, "field": field}


def sorted_inputs(refs: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(refs, key=lambda r: (r["stage"], r["artifact_key"], r["field"]))


def lineage_block(fields: dict[str, LineageField]) -> LineageBlock:
    return {"lineage_version": LINEAGE_VERSION, "fields": fields}
