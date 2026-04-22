"""Workspace model — isolates data per user/family."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    family_surname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # A6b (ADR-106): opt-in por workspace para usar DBArtifactStore.
    # None → usa flag global MATHOMS_USE_DB_ARTIFACTS; True → força DB; False → força Disk.
    use_db_artifacts_override: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, default=None
    )

    # Soft-delete (P1.2 · ADR-072). When not null, workspace is in "deleted"
    # state — hard-delete happens via janitor job after grace period (30 days).
    # Tenancy dependency (`get_current_workspace`) filters these out.
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    owner = relationship("User", back_populates="workspaces")
    reports = relationship("Report", back_populates="workspace", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="workspace", cascade="all, delete-orphan")
    vault_passwords = relationship(
        "PasswordVault", back_populates="workspace", cascade="all, delete-orphan"
    )
    pipeline_runs = relationship(
        "PipelineRun", back_populates="workspace", cascade="all, delete-orphan"
    )

    # Phase 3 — config relationships
    family_members = relationship(
        "FamilyMember", back_populates="workspace", cascade="all, delete-orphan"
    )
    categories = relationship("Category", back_populates="workspace", cascade="all, delete-orphan")
    pipeline_config = relationship(
        "PipelineConfig", back_populates="workspace", uselist=False, cascade="all, delete-orphan"
    )
    institution_config = relationship(
        "InstitutionConfig", back_populates="workspace", uselist=False, cascade="all, delete-orphan"
    )
    report_layout = relationship(
        "ReportLayout", back_populates="workspace", uselist=False, cascade="all, delete-orphan"
    )

    # Phase 4 — LLM config
    llm_config = relationship(
        "LLMConfig", back_populates="workspace", uselist=False, cascade="all, delete-orphan"
    )

    # Phase 6 — transactions & notifications
    transaction_overrides = relationship(
        "TransactionOverride", back_populates="workspace", cascade="all, delete-orphan"
    )
    notifications = relationship(
        "Notification", back_populates="workspace", cascade="all, delete-orphan"
    )

    # F8 / ADR-072 — membership (N:N user↔workspace)
    members = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    # F9 — convites pendentes/aceitos/revogados
    invitations = relationship(
        "WorkspaceInvitation",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
