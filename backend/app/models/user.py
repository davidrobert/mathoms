"""User model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy import false as sa_false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_developer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa_false()
    )
    # F9 · token invalidation — incrementado ao remover user de workspace.
    # JWT carrega `tv` claim; `decode_access_token` rejeita tokens stale.
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    # ADR-072 — membership em workspaces (pode pertencer a múltiplos)
    memberships = relationship(
        "WorkspaceMember",
        back_populates="user",
        foreign_keys="WorkspaceMember.user_id",
        cascade="all, delete-orphan",
    )
