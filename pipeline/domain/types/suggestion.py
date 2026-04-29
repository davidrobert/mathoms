"""Tipos puros do gerador de Suggestion (Direção E · Onda 5 · ADR-153).

Esses dataclasses vivem em ``pipeline/domain/types/`` para serem
importáveis por ``pipeline/domain/services/suggestion_generator.py``
sem trazer SQLAlchemy/FastAPI via transitivos do backend.

Backend converte para ``backend.app.models.suggestion.Suggestion`` no
use case :func:`backend.app.application.suggestions.regenerate_for_report`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional

Severity = Literal["info", "warning", "danger"]
Origin = Literal["deterministic", "llm"]

VALID_KINDS = frozenset(
    {
        "trs_desalinhada",
        "reserva_insuficiente",
        "alocacao_fora_alvo",
        "aporte_abaixo_meta",
        "dolarizacao_atrasada",
    }
)


@dataclass(frozen=True)
class SuggestionDraft:
    """Sugestão proposta antes de persistência. Imutável."""

    section_id: str
    kind: str
    severity: Severity
    title: str
    rationale: str
    dedup_key: str
    amount_brl: Optional[Decimal] = None
    origin: Origin = "deterministic"

    def __post_init__(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(f"kind inválido: {self.kind!r}; aceitos: {sorted(VALID_KINDS)}")
        if self.severity not in ("info", "warning", "danger"):
            raise ValueError(f"severity inválida: {self.severity!r}")
        if self.origin not in ("deterministic", "llm"):
            raise ValueError(f"origin inválida: {self.origin!r}")
        if not self.section_id or not self.title or not self.rationale:
            raise ValueError("section_id/title/rationale são obrigatórios e não-vazios")
        if not self.dedup_key or len(self.dedup_key) < 8:
            raise ValueError("dedup_key precisa ≥ 8 chars")
