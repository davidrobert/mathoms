"""DTOs do ``SnapshotChangelogBuilder`` no wire (v2.8 · ADR-148).

Pydantic adapters de ``ComparisonItem``/``ChangelogEntry`` (dataclasses do
domínio) para serialização JSON em ``GET /reports/{id}/data``. Money via
``MoneyBRL`` (Decimal em memória, number no wire — ADR-090).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from backend.app.schemas.money import MoneyBRL
from pipeline.domain.types.snapshot_changelog import (
    ChangelogEntry,
    ComparisonItem,
)

DeltaSignalRead = Literal["up", "down", "stable"]


class ComparisonItemRead(BaseModel):
    """Item de comparação seção-a-seção (v2.8). ``delta_pct=null`` em edges com zero."""

    section_id: str
    section_label: str
    before: MoneyBRL
    after: MoneyBRL
    delta_pct: Optional[MoneyBRL] = None
    delta_signal: DeltaSignalRead


class ChangelogEntryRead(BaseModel):
    """Entrada do changelog renderizado (uma por seção que cruza threshold)."""

    section_id: str
    summary: str
    delta_signal: DeltaSignalRead
    delta_pct: Optional[MoneyBRL] = None


def comparison_item_to_read(item: ComparisonItem) -> ComparisonItemRead:
    """Converte dataclass de domínio → DTO Pydantic."""
    return ComparisonItemRead(
        section_id=item.section_id,
        section_label=item.section_label,
        before=item.before,
        after=item.after,
        delta_pct=item.delta_pct,
        delta_signal=item.delta_signal,
    )


def changelog_entry_to_read(entry: ChangelogEntry) -> ChangelogEntryRead:
    """Converte dataclass de domínio → DTO Pydantic."""
    return ChangelogEntryRead(
        section_id=entry.section_id,
        summary=entry.summary,
        delta_signal=entry.delta_signal,
        delta_pct=entry.delta_pct,
    )


__all__ = [
    "ChangelogEntryRead",
    "ComparisonItemRead",
    "DeltaSignalRead",
    "changelog_entry_to_read",
    "comparison_item_to_read",
]
