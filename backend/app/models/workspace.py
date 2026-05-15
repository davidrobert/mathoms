"""Workspace model — isolates data per user/family."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String
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

    # FinOps (post-review fix 0.3): cap mensal de gasto LLM em USD para alarme.
    # Default 5.0 (free tier conservador); Premium pode subir via UI admin.
    # NÃO bloqueia chamadas — só dispara alerta no endpoint /v1/admin/llm-cost.
    monthly_llm_budget_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("5.00"), server_default="5.00"
    )

    # Soft-delete (P1.2 · ADR-072). When not null, workspace is in "deleted"
    # state — hard-delete happens via janitor job after grace period (30 days).
    # Tenancy dependency (`get_current_workspace`) filters these out.
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Sprint A10.7 — perfil tributário/PJ do cliente (substitui chave
    # `tributario` da bag PLANNING_CONTEXT do legado goals.json). JSON
    # livre validado por `BusinessProfile` Pydantic no boundary HTTP.
    business_profile_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)

    # ADR-188 §D6 — B2B2C consultor profissional pode subir o hard cap
    # default (``RULE_HARD_CAP=200``) para clientes com necessidades
    # específicas. None = usa default global. Valor efetivo:
    # ``COALESCE(rule_cap_override, RULE_HARD_CAP)``.
    rule_cap_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)

    # ADR-215 — estado tripartite da residência principal da família.
    # ``owned``: tem residência (exige 1 row WorkspacePropertyOverride
    # com classification='residencia_principal'); ``rented``: aluga
    # (linha "Residência" some do relatório); ``undeclared``: ainda não
    # respondeu (default; mostra `—` + CTA).
    residencia_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="undeclared", server_default="undeclared"
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
    transfer_config = relationship(
        "TransferConfig", back_populates="workspace", uselist=False, cascade="all, delete-orphan"
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
