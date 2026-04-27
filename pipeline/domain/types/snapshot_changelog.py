"""Tipos do ``SnapshotChangelogBuilder`` (v2.D.1 · ADR-143)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Mapping

DeltaSignal = Literal["up", "down", "stable"]


class UnknownSectionError(ValueError):
    """``section_id`` inválido — fail-fast em boundary (ADR-097)."""


@dataclass(frozen=True)
class AnalyzeFinancesSnapshot:
    """Snapshot E5 (`analyze_finances`); identidade `analysis_hash` derivada on-read."""

    workspace_id: str
    period_yyyymm: str
    analysis_hash: str
    content_json: Mapping[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class ComparisonItem:
    """Delta numérico de uma seção entre snapshots; `delta_pct=None` em edges com zero."""

    section_id: str
    section_label: str
    before: Decimal
    after: Decimal
    delta_pct: Decimal | None
    delta_signal: DeltaSignal


@dataclass(frozen=True)
class ChangelogEntry:
    """Linha do changelog renderizado por seção que cruza threshold."""

    section_id: str
    summary: str
    delta_signal: DeltaSignal
    delta_pct: Decimal | None


@dataclass(frozen=True)
class ComparisonResult:
    """Saída do builder; `has_previous=False` ⇒ items/entries vazios."""

    items: tuple[ComparisonItem, ...]
    entries: tuple[ChangelogEntry, ...]
    has_previous: bool


@dataclass(frozen=True)
class SnapshotChangelogConfig:
    """Configuração tipada (ADR-097 D3 value object)."""

    sections_to_compare: tuple[str, ...] = ("S1", "S2", "S3", "T2", "T5")
    minimum_delta_pct: Decimal = Decimal("0.5")
    thresholds: Mapping[str, Decimal] | None = None
    section_labels: Mapping[str, str] | None = None

    def threshold_for(self, section_id: str) -> Decimal:
        """Threshold efetivo (override > default)."""
        if self.thresholds and section_id in self.thresholds:
            return self.thresholds[section_id]
        return self.minimum_delta_pct

    def label_for(self, section_id: str) -> str:
        """Label efetivo (override > section_id)."""
        if self.section_labels and section_id in self.section_labels:
            return self.section_labels[section_id]
        return section_id


__all__ = [
    "AnalyzeFinancesSnapshot",
    "ChangelogEntry",
    "ComparisonItem",
    "ComparisonResult",
    "DeltaSignal",
    "SnapshotChangelogConfig",
    "UnknownSectionError",
]
