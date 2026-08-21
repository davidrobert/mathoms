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
# FP-2 D1-A: o changelog admite um 4º estado que a célula de comparação não tem —
# sob base alterada o juízo é recolhido, não invertido nem zerado.
ChangelogSignalRead = Literal["up", "down", "stable", "nao_comparavel"]
ComparabilidadeRead = Literal["comparavel", "base_alterada"]
DirectionPositiveRead = Literal["up", "down"]
MetricUnitRead = Literal["brl", "pp", "meses"]


class ComparisonItemRead(BaseModel):
    """Item de comparação seção-a-seção (v2.8). ``delta_pct=null`` em edges com zero."""

    # direction_positive (W2 · ADR-190 D3): direção "boa pro usuário" — a UI
    # inverte a cor quando delta_signal != direction_positive.
    section_id: str
    section_label: str
    before: MoneyBRL
    after: MoneyBRL
    delta_pct: Optional[MoneyBRL] = None
    delta_signal: DeltaSignalRead
    direction_positive: DirectionPositiveRead = "up"
    # unit (v3 · ADR-190 §Emenda 2026-07-09): "pp"/"meses" exibem delta
    # absoluto (after−before) formatado na unidade; "brl" mantém money.
    unit: MetricUnitRead = "brl"


class ChangelogEntryRead(BaseModel):
    """Entrada do changelog renderizado (uma por seção que cruza threshold)."""

    section_id: str
    summary: str
    delta_signal: ChangelogSignalRead
    delta_pct: Optional[MoneyBRL] = None
    # Marcador é DIFERENÇA, não presença: "comparavel" é o default e não anota nada.
    comparabilidade: ComparabilidadeRead = "comparavel"


def comparison_item_to_read(item: ComparisonItem) -> ComparisonItemRead:
    """Converte dataclass de domínio → DTO Pydantic."""
    return ComparisonItemRead(
        section_id=item.section_id,
        section_label=item.section_label,
        before=item.before,
        after=item.after,
        delta_pct=item.delta_pct,
        delta_signal=item.delta_signal,
        direction_positive=item.direction_positive,
        unit=item.unit,
    )


def changelog_entry_to_read(entry: ChangelogEntry) -> ChangelogEntryRead:
    """Converte dataclass de domínio → DTO Pydantic."""
    return ChangelogEntryRead(
        section_id=entry.section_id,
        summary=entry.summary,
        delta_signal=entry.delta_signal,
        delta_pct=entry.delta_pct,
    )


_RESSALVA_BASE_ALTERADA = "base de comparação alterada entre os relatórios"


# Mantém ``delta_pct`` — some o juízo, não o número (FP-2 D1-A). A ressalva entra no
# ``summary`` porque o template já afirma "cresceu/recuou … desde o relatório anterior",
# e esse texto é emendado ao parágrafo de abertura da seção no renderer: deixar a prosa
# intacta contradiz o ``delta_signal`` do próprio objeto e chega assim ao leitor.
def neutralize_changelog_base_changed(
    entries: list[ChangelogEntryRead],
) -> list[ChangelogEntryRead]:
    """Recolhe o juízo do changelog quando as pontas do par vieram de métodos diferentes."""
    return [
        entry.model_copy(
            update={
                "delta_signal": "nao_comparavel",
                "comparabilidade": "base_alterada",
                "summary": f"{entry.summary} — {_RESSALVA_BASE_ALTERADA}",
            }
        )
        for entry in entries
    ]


__all__ = [
    "ChangelogEntryRead",
    "ChangelogSignalRead",
    "ComparabilidadeRead",
    "ComparisonItemRead",
    "DeltaSignalRead",
    "DirectionPositiveRead",
    "MetricUnitRead",
    "changelog_entry_to_read",
    "neutralize_changelog_base_changed",
    "comparison_item_to_read",
]
