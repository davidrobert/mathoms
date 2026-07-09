"""Tipos do ``SnapshotChangelogBuilder`` (v2.D.1 · ADR-148)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Mapping

DeltaSignal = Literal["up", "down", "stable"]

DirectionPositive = Literal["up", "down"]

# Unidade de exibição da métrica (ADR-190 §Emenda 2026-07-09): "brl" formata
# monetário; "pp"/"meses" exibem delta absoluto (after−before), não delta_pct.
MetricUnit = Literal["brl", "pp", "meses"]

# Direção "positiva pro usuário" por seção (ADR-190 D3): asset → up é bom;
# expense → down é bom. Espelha SECTION_POLARITY de narratives.py (asset↔up,
# expense↔down) — consistência travada por teste.
DEFAULT_DIRECTION_POSITIVE: Mapping[str, DirectionPositive] = {
    "S1": "up",
    "S2": "up",
    "S3": "up",
    "T2": "up",
    "T5": "down",
    "M_PL": "up",
    "M_TAXA_POUPANCA": "up",
    "M_RESERVA_MESES": "up",
    "M_AUVP_DESVIO": "down",
}

# Unidade de exibição por métrica canônica (default "brl" para ids legados).
DEFAULT_METRIC_UNITS: Mapping[str, MetricUnit] = {
    "M_PL": "brl",
    "M_TAXA_POUPANCA": "pp",
    "M_RESERVA_MESES": "meses",
    "M_AUVP_DESVIO": "pp",
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
    unit: MetricUnit = "brl"


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

    # Default v3 (ADR-190 §Emenda 2026-07-09): métricas canônicas sobre campos
    # E5 reais, MoM uniforme. Ids legados (S1/S2/S3/T2/T5) seguem válidos via
    # override explícito (retrocompat D1).
    sections_to_compare: tuple[str, ...] = (
        "M_PL",
        "M_TAXA_POUPANCA",
        "M_RESERVA_MESES",
        "M_AUVP_DESVIO",
    )
    minimum_delta_pct: Decimal = Decimal("0.5")
    thresholds: Mapping[str, Decimal | ThresholdRule] | None = None
    section_labels: Mapping[str, str] | None = None
    direction_positive: Mapping[str, DirectionPositive] | None = None

    def threshold_rule_for(self, section_id: str) -> ThresholdRule:
        """Regra efetiva (override > default por métrica > pct global legado)."""
        if self.thresholds and section_id in self.thresholds:
            override = self.thresholds[section_id]
            if isinstance(override, ThresholdRule):
                return override
            return ThresholdRule(pct=override)
        if section_id in DEFAULT_METRIC_THRESHOLDS:
            return DEFAULT_METRIC_THRESHOLDS[section_id]
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


# Thresholds default por métrica canônica (ADR-190 D4 + §Emenda 2026-07-09).
# `abs_brl` é o limite ABSOLUTO na unidade da própria métrica (R$ para brl,
# pontos para pp, meses para meses) — nome preservado do W2 por compat.
DEFAULT_METRIC_THRESHOLDS: Mapping[str, ThresholdRule] = {
    "M_PL": ThresholdRule(pct=Decimal("2"), abs_brl=Decimal("20000")),
    "M_TAXA_POUPANCA": ThresholdRule(abs_brl=Decimal("3")),
    "M_RESERVA_MESES": ThresholdRule(abs_brl=Decimal("0.5")),
    "M_AUVP_DESVIO": ThresholdRule(abs_brl=Decimal("2")),
}


__all__ = [
    "AnalyzeFinancesSnapshot",
    "DEFAULT_METRIC_THRESHOLDS",
    "DEFAULT_METRIC_UNITS",
    "MetricUnit",
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
