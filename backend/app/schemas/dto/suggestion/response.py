"""Response DTOs do aggregate ``Suggestion`` (ADR-153).

Money em wire como string decimal (``amount_brl``) — frontend renderiza
via ``<MonetaryValue/>``.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SuggestionResponse(BaseModel):
    """Sugestão projetada — o que a UI consome."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    report_id: Optional[str] = None
    section_id: str
    kind: str
    category: Optional[str] = None  # ADR-161 — agrupamento semântico
    origin: str
    severity: str
    title: str
    rationale: str
    amount_brl: Optional[Decimal] = None
    # Exposto para o frontend resolver Suggestion ↔ Parecer (ADR-199 Ato 5):
    # parecer LLM emite `suggestion_dedup_key`; UI usa para resolver `id`
    # antes de chamar /accept ou /dismiss. Não é PII.
    dedup_key: str
    status: str
    accepted_decision_id: Optional[str] = None
    # ADR-214 — code da Decision criada (populado pelos use cases
    # ``accept_suggestion`` / ``modify_suggestion``). UI exibe em toast
    # pós-aceite: ``"Decisão D03 criada"``. Sempre ``None`` no get/list —
    # só faz sentido como side-effect da transição Pendente→Aceita.
    accepted_decision_code: Optional[str] = None
    dismissed_reason: Optional[str] = None
    accepted_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SuggestionListResponse(BaseModel):
    suggestions: list[SuggestionResponse]
    total: int


class SuggestionCountResponse(BaseModel):
    count: int
    status: Optional[str] = None


class SuggestionRegenerateResponse(BaseModel):
    """Resultado de uma regeneração — quantas drafts viraram persisted."""

    created: int
    skipped_dedup: int
    skipped_cap: int
    total_drafts: int
    suggestions: list[SuggestionResponse]


class SuggestionsSummaryResponse(BaseModel):
    """Sumário de sugestões pendentes (ADR-161 · Onda 8 #5).

    Substitui ``SuggestionCountResponse`` em call-sites que precisam
    refletir severidade (banner em /plano). Retorna ``count``,
    ``max_severity`` (severidade dominante para tom do banner) e
    ``by_category`` (contagem agrupada para hover/filtros).
    """

    count: int
    max_severity: Optional[str] = None  # "danger" | "warning" | "info" | None
    by_category: dict[str, int] = {}  # noqa: RUF012
