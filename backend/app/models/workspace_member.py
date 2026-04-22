"""WorkspaceMember — membership join table entre User e Workspace (ADR-072).

Um usuário pode pertencer a múltiplos workspaces (advisor com várias
famílias) e um workspace pode ter múltiplos usuários (casal, contador
convidado). Este model substitui o uso exclusivo de `Workspace.owner_id`
como filtro de acesso: `owner_id` fica como "criador original" para audit,
mas a autorização é feita aqui.

Roles (F9.0):
- `owner`:  criador do workspace; permissões totais (inclusive delete + gestão de membros)
- `member`: acesso total de leitura e escrita, exceto delete do workspace e gestão de membros
- `viewer`: read-only — não pode criar/editar metas, transações, documentos

RBAC mais granular (approver, admin) continua como débito explícito — ver
ADR-072 §"Débito explícito".
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

# Roles aceitas. Mantido como set literal (não Enum) para permitir
# evolução sem migration; validação explícita no service layer.
VALID_ROLES: frozenset[str] = frozenset({"owner", "member", "viewer"})

# Roles que podem fazer WRITE. `viewer` é read-only.
WRITE_ROLES: frozenset[str] = frozenset({"owner", "member"})

# Roles que podem gerenciar membros (convidar, remover, mudar roles).
# Por ora restrito ao owner — ver ADR-072 §débito.
MEMBER_ADMIN_ROLES: frozenset[str] = frozenset({"owner"})


class WorkspaceMember(Base):
    """Relação N:N entre `users` e `workspaces` com `role` e metadados de convite.

    Constraint: (workspace_id, user_id) é único. Um usuário só pode ter
    uma linha por workspace — mudança de role é UPDATE, não novo registro.
    """

    __tablename__ = "workspace_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    invited_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="memberships")
    inviter = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
        Index("ix_workspace_members_ws_user", "workspace_id", "user_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WorkspaceMember ws={self.workspace_id} user={self.user_id} role={self.role}>"
