"""``LLMDriftCheck`` — resultado estrutural do drift nightly por fixture (A33.l5 · ADR-307 F2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class LLMDriftCheck(Base):
    """1 row por fixture por execução do drift-check; pass/fail consultável.

    Sem FK de workspace por design: o drift-check avalia o contrato global
    do prompt/provider, não dado de tenant. Custo e tenancy da chamada ficam
    no ``llm_call_log`` (hooks ADR-173); esta tabela existe porque cache hit
    não grava ``LLMCallLog`` (ADR-307 D5) e linha de custo prova chamada,
    não avaliação.
    """

    __tablename__ = "llm_drift_check"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    fixture_id: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Lista de mensagens estruturais (valor ofensor + shape esperado); NULL = pass.
    failures: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    __table_args__ = (Index("ix_llm_drift_check_stage_created", "stage", "created_at"),)
