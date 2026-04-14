"""Workspace model — isolates data per user/family."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    owner = relationship("User", back_populates="workspaces")
    reports = relationship("Report", back_populates="workspace", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="workspace", cascade="all, delete-orphan")
    vault_passwords = relationship("PasswordVault", back_populates="workspace", cascade="all, delete-orphan")
    pipeline_runs = relationship("PipelineRun", back_populates="workspace", cascade="all, delete-orphan")

    # Phase 3 — config relationships
    family_members = relationship("FamilyMember", back_populates="workspace", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="workspace", cascade="all, delete-orphan")
    pipeline_config = relationship("PipelineConfig", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    institution_config = relationship("InstitutionConfig", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    report_layout = relationship("ReportLayout", back_populates="workspace", uselist=False, cascade="all, delete-orphan")

    # Phase 4 — LLM config
    llm_config = relationship("LLMConfig", back_populates="workspace", uselist=False, cascade="all, delete-orphan")

    # Phase 6 — transactions & notifications
    transaction_overrides = relationship("TransactionOverride", back_populates="workspace", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="workspace", cascade="all, delete-orphan")
