"""WorkspaceInvitation — convite pendente para virar membro de um workspace (F9).

Fluxo:

1. Owner chama `POST /workspaces/{ws}/invitations` com `email` + `role`.
2. Service gera token aleatório (`secrets.token_urlsafe(32)`), armazena
   `sha256(token)` e devolve o token **cru** UMA vez na resposta.
3. Owner envia o link manualmente (WhatsApp/SMS/pessoalmente) — solução
   F9.1 sem provider de email. F9.8 liga envio automático flipando uma
   chave; o modelo não muda.
4. Convidado abre `/invite/{token}`, faz login/signup, chama
   `POST /invitations/{token}/accept` → cria `WorkspaceMember`.
5. TTL 72h. Uso único. Pode ser revogado pelo owner antes do aceite.

Estados derivados (não persistidos em coluna — calculados):

    pending  → accepted_at IS NULL AND revoked_at IS NULL AND expires_at > now
    accepted → accepted_at IS NOT NULL
    revoked  → revoked_at IS NOT NULL
    expired  → expires_at <= now AND accepted_at IS NULL AND revoked_at IS NULL

Estados são terminais — convite aceito/revogado/expirado não volta. Para
reenviar: crie um novo convite (o token antigo passa a ser inútil).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class WorkspaceInvitation(Base):
    """Convite pendente para alguém entrar em um workspace."""

    __tablename__ = "workspace_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)

    # Armazenamos SHA-256 hex (64 chars) do token; o token cru existe só
    # no corpo da resposta de criação e no link. Se vazar o DB, convites
    # não viram vetor de ataque.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    invited_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workspace = relationship("Workspace", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])
    acceptor = relationship("User", foreign_keys=[accepted_by_user_id])

    __table_args__ = (Index("ix_workspace_invitations_ws_email", "workspace_id", "email"),)

    def is_pending(self, now: Optional[datetime] = None) -> bool:
        """True se o convite ainda é utilizável (não aceito, não revogado,
        não expirado)."""
        now = now or datetime.now(timezone.utc)
        # SQLite armazena DateTime sem tz — normalizamos para UTC antes de
        # comparar, caso contrário `naive > aware` levanta TypeError.
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return self.accepted_at is None and self.revoked_at is None and exp > now

    def status(self, now: Optional[datetime] = None) -> str:
        """Retorna `'pending' | 'accepted' | 'revoked' | 'expired'`."""
        if self.accepted_at is not None:
            return "accepted"
        if self.revoked_at is not None:
            return "revoked"
        now = now or datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= now:
            return "expired"
        return "pending"

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<WorkspaceInvitation ws={self.workspace_id} "
            f"email={self.email} role={self.role} status={self.status()}>"
        )
