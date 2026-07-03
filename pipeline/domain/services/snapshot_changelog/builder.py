"""``SnapshotChangelogBuilder`` — comparações mês-a-mês determinísticas (v2.D.1 · ADR-148)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from pipeline.domain.services.snapshot_changelog.narratives import format_summary
from pipeline.domain.types.snapshot_changelog import (
    AnalyzeFinancesSnapshot,
    ChangelogEntry,
    ComparisonItem,
    ComparisonResult,
    DeltaSignal,
    SnapshotChangelogConfig,
    ThresholdRule,
    UnknownSectionError,
)

# section_id → dotted path em `content_json` (default; expandir em v2.D.1.x).
DEFAULT_SECTION_VALUE_PATHS: Mapping[str, str] = {
    "S1": "patrimonio.liquido",
    "S2": "fluxo_caixa.receita_total",
    "S3": "patrimonio.bruto",
    "T2": "fluxo_caixa.investimentos_total",
    "T5": "fluxo_caixa.despesa_total",
}

DEFAULT_SECTION_LABELS: Mapping[str, str] = {
    "S1": "Patrimônio Líquido",
    "S2": "Receita Total",
    "S3": "Patrimônio Bruto",
    "T2": "Aportes",
    "T5": "Despesas Totais",
}


def build_comparison(
    prev: AnalyzeFinancesSnapshot | None,
    curr: AnalyzeFinancesSnapshot,
    config: SnapshotChangelogConfig,
) -> ComparisonResult:
    """Entry point: compara snapshots; `prev=None` ⇒ result vazio com `has_previous=False`."""
    if prev is None:
        return ComparisonResult(items=(), entries=(), has_previous=False)
    items = tuple(
        _compare_section(section_id, prev, curr, config)
        for section_id in config.sections_to_compare
    )
    entries = tuple(_make_entry(item) for item in items if _crosses_threshold(item))
    return ComparisonResult(items=items, entries=entries, has_previous=True)


def _compare_section(
    section_id: str,
    prev: AnalyzeFinancesSnapshot,
    curr: AnalyzeFinancesSnapshot,
    config: SnapshotChangelogConfig,
) -> ComparisonItem:
    """Computa delta de uma seção; fail-fast se `section_id` desconhecido."""
    before = extract_section_value(prev.content_json, section_id)
    after = extract_section_value(curr.content_json, section_id)
    label = _resolve_label(section_id, config)
    delta_pct, signal = _compute_delta(before, after, config.threshold_rule_for(section_id))
    return ComparisonItem(
        section_id=section_id,
        section_label=label,
        before=before,
        after=after,
        delta_pct=delta_pct,
        delta_signal=signal,
        direction_positive=config.direction_positive_for(section_id),
    )


def extract_section_value(content_json: Mapping[str, Any], section_id: str) -> Decimal:
    """Resolve `section_id` → `Decimal` via DEFAULT_SECTION_VALUE_PATHS; raise se desconhecido."""
    if section_id not in DEFAULT_SECTION_VALUE_PATHS:
        raise UnknownSectionError(
            f"section_id={section_id!r} sem path mapeado "
            f"(disponíveis={tuple(DEFAULT_SECTION_VALUE_PATHS.keys())!r})"
        )
    raw = _navigate_dotted(content_json, DEFAULT_SECTION_VALUE_PATHS[section_id])
    return _coerce_decimal(raw)


def _navigate_dotted(data: Mapping[str, Any], dotted: str) -> Any:
    """Walk dotted path; retorna None se chave intermediária ausente."""
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _coerce_decimal(value: Any) -> Decimal:
    """Converte float/int/str/None → `Decimal` via str() para float (ADR-090)."""
    if value is None or isinstance(value, bool):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal("0")


def _compute_delta(
    before: Decimal,
    after: Decimal,
    rule: ThresholdRule,
) -> tuple[Decimal | None, DeltaSignal]:
    """Computa `delta_pct` em pontos percentuais e signal pela regra dual (D4)."""
    if before == 0:
        return _delta_when_before_zero(after)
    if after == 0:
        signal: DeltaSignal = "down" if before > 0 else "up"
        return None, signal
    delta_pct = (after - before) / before * Decimal("100")
    return delta_pct, _classify_signal(delta_pct, after - before, rule)


def _delta_when_before_zero(after: Decimal) -> tuple[Decimal | None, DeltaSignal]:
    """Caso edge `before=0`: both_zero stable, from_zero up/down sem pct."""
    if after == 0:
        return Decimal("0"), "stable"
    return None, "up" if after > 0 else "down"


def _classify_signal(
    delta_pct: Decimal,
    delta_abs: Decimal,
    rule: ThresholdRule,
) -> DeltaSignal:
    """`stable` só se TODOS os limites definidos ficam abaixo (critério W2);
    cruzar qualquer limite (>=) sinaliza."""
    pct_crossed = rule.pct is not None and abs(delta_pct) >= rule.pct
    abs_crossed = rule.abs_brl is not None and abs(delta_abs) >= rule.abs_brl
    if not pct_crossed and not abs_crossed:
        return "stable"
    return "up" if delta_pct > 0 else "down"


def _crosses_threshold(item: ComparisonItem) -> bool:
    """Filtra changelog: signal não-stable (inclui edge cases zero)."""
    return item.delta_signal != "stable"


def _make_entry(item: ComparisonItem) -> ChangelogEntry:
    """Render de `ChangelogEntry` a partir de `ComparisonItem`."""
    return ChangelogEntry(
        section_id=item.section_id,
        summary=format_summary(item),
        delta_signal=item.delta_signal,
        delta_pct=item.delta_pct,
    )


def _resolve_label(section_id: str, config: SnapshotChangelogConfig) -> str:
    """Label efetivo: config override > DEFAULT_SECTION_LABELS > section_id."""
    if config.section_labels and section_id in config.section_labels:
        return config.section_labels[section_id]
    if section_id in DEFAULT_SECTION_LABELS:
        return DEFAULT_SECTION_LABELS[section_id]
    return section_id
