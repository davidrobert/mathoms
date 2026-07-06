"""PlannerFieldRequest — telemetria de campo faltante (ADR-206 M4). Privacy-by-construction: ``field_path`` é estrutural (JSONPath), nunca persiste valor cliente."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

# Reasons aceitos quando origem é tool_trace `found:false` (ADR-203 §D7).
# None = origem fonte primária (LLM declarou em ``campos_faltantes_pediria_se_iterasse[]``).
# field_request_spurious / field_request_wrong_path (A28.l11): entradas removidas
# pelo filtro 3-vias pós-LLM (path resolve não-nulo / alias conhecido não-nulo) —
# persistidas para telemetria; wrong_path alimenta expansão do manifest.
VALID_FIELD_REQUEST_REASONS: frozenset[str] = frozenset(
    {
        "path_not_whitelisted",
        "value_null",
        "value_absent",
        "llm_declared",
        "field_request_spurious",
        "field_request_wrong_path",
    }
)


class PlannerFieldRequest(Base):
    """Row por (parecer, field_path) — alimenta dashboard semanal top-10 (ADR-206 §D4)."""

    __tablename__ = "planner_field_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    planner_review_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("planner_review_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # JSONPath subset (ADR-200 DSL) — estrutural, sem valor cliente.
    field_path: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Motivo curto-textual (LLM emite); reason categórico fica em ``reason``.
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    # Origem: ``llm_declared`` (fonte primária) ou tool_trace error code (ADR-206 §D2).
    reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        # ADR-206 §D1 — um parecer não duplica o mesmo path no array.
        UniqueConstraint(
            "planner_review_id", "field_path", name="uq_planner_field_request_review_path"
        ),
        # Agregação top-N por janela temporal.
        Index("ix_planner_field_requests_date_path", "created_at", "field_path"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PlannerFieldRequest review={self.planner_review_id} path={self.field_path!r}>"


__all__ = ["PlannerFieldRequest", "VALID_FIELD_REQUEST_REASONS"]
