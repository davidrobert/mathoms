"""Contrato comum de dedup de entidades patrimoniais no E1.5c (ADR-276):
runner ``run_entity_dedup`` + ``EntityDedupPolicy`` (3 membros) unificam o
esqueleto de ``imoveis_dedup`` (ADR-246/265) e ``investimentos_dedup``
(ADR-271) — agrupar por identidade (ordem de inserção é invariante; runner
NÃO reordena) → reagrupar (declarado) → ``emit_group`` (único dono do merge;
devolve ``(entries, warnings, dropped_ids)``, runner só concatena, nunca
re-injeta warning) → montar ``DedupOutcome`` + log.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger("mathoms.pipeline.consolidate")

GroupedEntries = list[tuple[tuple, list[dict]]]  # (identity_key, entries), ordenado


@dataclass(frozen=True)
class DedupWarning:
    entity_id: str | None
    type: str
    values: tuple[float, ...]
    diff_pct: float


@dataclass(frozen=True)
class DedupOutcome:
    items: list[dict]
    warnings: tuple[DedupWarning, ...]
    count_before: int
    count_after: int
    dropped_ids: tuple[str, ...]


class EntityDedupPolicy(Protocol):
    """Estratégia de dedup de um tipo de entidade. Ver ADR-276."""

    def identity_key(self, entry: dict) -> tuple | None:
        """Chave de identidade do grupo; ``None`` = unidentified (passa intacto)."""
        ...

    def remap_groups(self, grouped: GroupedEntries) -> GroupedEntries:
        """Reagrupa por identidade secundária (fuzzy/cross-código); total, não
        opcional — domínios sem reagrupamento retornam ``grouped`` intacto."""
        ...

    def emit_group(
        self, group: list[dict]
    ) -> tuple[list[dict], tuple[DedupWarning, ...], tuple[str, ...]]:
        """Funde/emite um grupo → (entries de saída, warnings, ids descartados)."""
        ...


def run_entity_dedup(items: list[dict] | None, policy: EntityDedupPolicy) -> DedupOutcome:
    """Aplica ``policy`` sobre ``items`` preservando a ordem de inserção (ADR-276);
    puro (sem side-effect) — observabilidade fica no wrapper via ``log_dedup``."""
    entries = [e for e in (items or []) if isinstance(e, dict)]
    grouped, unidentified = _group_by_identity(entries, policy)
    grouped = policy.remap_groups(grouped)
    out, warnings, dropped = _emit_all(grouped, policy)
    out.extend(unidentified)
    return DedupOutcome(
        items=out,
        warnings=tuple(warnings),
        count_before=len(entries),
        count_after=len(out),
        dropped_ids=tuple(dropped),
    )


def _group_by_identity(
    entries: list[dict], policy: EntityDedupPolicy
) -> tuple[GroupedEntries, list[dict]]:
    grouped: dict[tuple, list[dict]] = {}
    order: list[tuple] = []
    unidentified: list[dict] = []
    for entry in entries:
        key = policy.identity_key(entry)
        if key is None:
            unidentified.append(entry)
            continue
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(entry)
    return [(key, grouped[key]) for key in order], unidentified


def _emit_all(
    grouped: GroupedEntries, policy: EntityDedupPolicy
) -> tuple[list[dict], list[DedupWarning], list[str]]:
    out: list[dict] = []
    warnings: list[DedupWarning] = []
    dropped: list[str] = []
    for _key, group in grouped:
        entries, group_warnings, group_dropped = policy.emit_group(group)
        out.extend(entries)
        warnings.extend(group_warnings)
        dropped.extend(group_dropped)
    return out, warnings, dropped


def log_dedup(event: str, outcome: DedupOutcome, *, dropped_key: str) -> None:
    """Log estruturado no-op quando nada foi deduplicado. ``dropped_key`` preserva
    o nome de campo legado por domínio (``dropped_keys`` / ``dropped_property_ids``)."""
    if outcome.count_after >= outcome.count_before:
        return
    logger.info(
        event,
        extra={
            "stage": "E1.5c",
            "count_before": outcome.count_before,
            "count_after": outcome.count_after,
            dropped_key: list(outcome.dropped_ids),
            "warnings_count": len(outcome.warnings),
        },
    )


__all__ = [
    "DedupOutcome",
    "DedupWarning",
    "EntityDedupPolicy",
    "GroupedEntries",
    "log_dedup",
    "run_entity_dedup",
]
