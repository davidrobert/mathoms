"""``InternalOpsAudit`` — trilha de mutação de operador do console interno (ADR-309).

Tabela separada de ``audit_logs`` (produto/LGPD, ADR-275): operador não é
``user`` (auth yaml, ADR-116) e o CASCADE de workspace apagaria o audit da
própria operação destrutiva. Sem FK por design; retenção indefinida (mínimo
5 anos), nenhum purge job toca esta tabela. Em Postgres o role da app tem
REVOKE UPDATE/DELETE (runbook de deploy) — imutabilidade real, não convenção.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class InternalOpsAudit(Base):
    __tablename__ = "internal_ops_audit"

    # ADR-309 D1: índice único no MVP — a UI só lê "últimas N" ordenadas;
    # índices por actor/action entram quando houver filtro.
    __table_args__ = (Index("ix_internal_ops_audit_created", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
