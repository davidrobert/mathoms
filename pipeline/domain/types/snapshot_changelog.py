"""Tipos do ``SnapshotChangelogBuilder`` (v2.D.1 · ADR-148)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Mapping

DeltaSignal = Literal["up", "down", "stable"]

DirectionPositive = Literal["up", "down"]

# Direção "positiva pro usuário" por seção (ADR-190 D3): asset → up é bom;
# expense → down é bom. Espelha SECTION_POLARITY de narratives.py (asset↔up,
# expense↔down) — consistência travada por teste.
DEFAULT_DIRECTION_POSITIVE: Mapping[str, DirectionPositive] = {
    "S1": "up",
    "S2": "up",
    "S3": "up",
    "T2": "up",
    "T5": "down",
}


class UnknownSectionError(ValueError):
    """``section_id`` inválido — fail-fast em boundary (ADR-097)."""


@dataclass(frozen=True)
class ThresholdRule:
    """Threshold dual por métrica (ADR-190 D4) — pp e/ou R$ absoluto; ≥1 limite obrigatório."""

    # `stable` somente se TODOS os limites definidos ficam abaixo (critério W2);
    # cruzar qualquer um sinaliza.
    pct: Decimal | None = None
    abs_brl: Decimal | None = None

    def __post_init__(self) -> None:
        if self.pct is None and self.abs_brl is None:
            raise ValueError("ThresholdRule exige pct e/ou abs_brl, got ambos None")


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
    direction_positive: DirectionPositive = "up"


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
    thresholds: Mapping[str, Decimal | ThresholdRule] | None = None
    section_labels: Mapping[str, str] | None = None
    direction_positive: Mapping[str, DirectionPositive] | None = None

    def threshold_rule_for(self, section_id: str) -> ThresholdRule:
        """Regra efetiva (override > default); `Decimal` legado vira regra pct-only."""
        if self.thresholds and section_id in self.thresholds:
            override = self.thresholds[section_id]
            if isinstance(override, ThresholdRule):
                return override
            return ThresholdRule(pct=override)
        return ThresholdRule(pct=self.minimum_delta_pct)

    def direction_positive_for(self, section_id: str) -> DirectionPositive:
        """Direção positiva efetiva (override > default D3 > 'up')."""
        if self.direction_positive and section_id in self.direction_positive:
            return self.direction_positive[section_id]
        return DEFAULT_DIRECTION_POSITIVE.get(section_id, "up")

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
    "DEFAULT_DIRECTION_POSITIVE",
    "DeltaSignal",
    "DirectionPositive",
    "SnapshotChangelogConfig",
    "ThresholdRule",
    "UnknownSectionError",
]
