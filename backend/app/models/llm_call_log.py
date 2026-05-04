"""``LLMCallLog`` — telemetria por chamada LLM para FinOps (post-review fix 0.3)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class LLMCallLog(Base):
    """1 row por LLM call agregada a workspace; cost_usd em Numeric (ADR-090 mirror)."""

    __tablename__ = "llm_call_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0.000000")
    )
    # cost_known=False quando modelo não estava em MODEL_PRICING — distingue
    # "desconhecido" de "grátis" (Ollama local). Ver pipeline/llm/pricing.py.
    cost_known: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pipeline_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    __table_args__ = (
        Index("ix_llm_call_log_ws_created", "workspace_id", "created_at"),
        Index("ix_llm_call_log_ws_model_created", "workspace_id", "model_name", "created_at"),
    )
