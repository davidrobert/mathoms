"""Filtros comuns a ``list_transactions`` e ``export_transactions``."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionFilters:
    member: str | None = None
    bank: str | None = None
    category: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    value_min: float | None = None
    value_max: float | None = None
    search: str | None = None
