"""Command DTOs do aggregate ``Suggestion`` (ADR-153).

Money em wire = string decimal (ADR-090); cents conversion no use case.
Aceitar/Modificar/Descartar/Regenerate são as operações públicas.
``SuggestionDraft`` (intermediário do gerador) vive em
:mod:`pipeline.domain.types.suggestion` — não é exposto via HTTP.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.suggestion import VALID_DISMISS_REASONS


class AcceptSuggestionCommand(BaseModel):
    """Aceita sugestão criando ``Decision`` com os campos sugeridos."""

    model_config = ConfigDict(extra="forbid")

    decision_code: str = Field(..., min_length=1, max_length=16)
    note: Optional[str] = None


class ModifySuggestionCommand(BaseModel):
    """Aceita com modificação — usuário customiza title/rationale/amount."""

    model_config = ConfigDict(extra="forbid")

    decision_code: str = Field(..., min_length=1, max_length=16)
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    rationale: Optional[str] = None
    amount_brl: Optional[Decimal] = None
    note: Optional[str] = None


class DismissSuggestionCommand(BaseModel):
    """Descarta sugestão com motivo controlado."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=1, max_length=32)
    note: Optional[str] = None

    @field_validator("reason")
    @classmethod
    def _validate_reason(cls, v: str) -> str:
        if v not in VALID_DISMISS_REASONS:
            raise ValueError(f"reason inválido: {v!r}; aceitos: {sorted(VALID_DISMISS_REASONS)}")
        return v


class RegenerateSuggestionsCommand(BaseModel):
    """Re-gera sugestões para um Report. Sem parâmetros por enquanto."""

    model_config = ConfigDict(extra="forbid")
