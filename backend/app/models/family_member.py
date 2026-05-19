"""FamilyMember model — a person in the family with encrypted CPF."""

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class FamilyMember(Base):
    __tablename__ = "family_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(100), nullable=False)
    cpf_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="titular")
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # ADR-192 §D4 — sinal estruturado de exposição fiscal americana, derivado
    # via ``ProtectionBundle.has_us_exposure``. Codes aceitos a nível
    # de aplicação: ``none`` (default), ``resident``,
    # ``former_resident_within_10y``, ``greencard_expiring``, ``citizen``.
    us_tax_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workspace = relationship("Workspace", back_populates="family_members")
    accounts: Mapped[list["BankAccount"]] = relationship(
        "BankAccount",
        back_populates="member",
        cascade="all, delete-orphan",
        order_by="BankAccount.id",
    )


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # ADR-226 PR1: denormalização do workspace_id do family_member dono.
    # Destrava o partial unique index do PR4 (PostgreSQL não suporta JOIN
    # em índice funcional). Backfill garantido pela migration.
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_code: Mapped[str] = mapped_column(String(50), nullable=False)
    account_type: Mapped[str] = mapped_column(String(100), nullable=False)
    agency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # ADR-146 (A7.6): override workspace-específico da hierarquia universal
    # de fontes E3. NULL = usar default Mathoms (resolvido em runtime por
    # tipo de fonte / parser do banco). 1 = mais confiável (extração LLM
    # estruturada), 5 = menos confiável (declaração editorial / IRPF).
    source_tier: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True, default=None)
    # ADR-226 PR1: conta conjunta — flag reservada em V1, ativada em V2
    # ADR follow-up (rateio proporcional Cerbasi-style). Sem consumidor
    # no pipeline em V1.
    is_joint: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # ADR-226 PR1: lista de member_id dos co-titulares quando is_joint=true.
    # Reservado em V1; V2 ativa rateio.
    co_titulares: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    member = relationship("FamilyMember", back_populates="accounts")
