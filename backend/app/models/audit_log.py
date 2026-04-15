"""AuditLog model — registra operações sensíveis por workspace.

Uso principal: rastrear upload / delete / export / purge de documentos em
`storage/{workspace_id}/`. Também aceita eventos de auth, config e pipeline
se a equipe decidir expandir.

O escopo mínimo (F6.5 hardening) cobre:
  - document.upload
  - document.delete
  - storage.purge (ao deletar workspace inteiro)
  - workspace.export

Campos de contexto (`actor_user_id`, `ip_address`, `user_agent`) são
opcionais — nem todo evento tem HTTP request associado (ex.: jobs Celery).

`metadata` é um JSON livre com detalhes do evento (filename, size, hash,
etc). Evite colocar PII que não esteja já em outras tabelas.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max 45
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    workspace = relationship("Workspace")
    actor = relationship("User")
