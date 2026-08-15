"""Fontes editáveis para computabilidade de proteção (ADR-387)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

VALID_DEPENDENCY_STATUSES = frozenset({"yes", "no", "unknown"})
VALID_PROTECTION_SOURCE_KINDS = frozenset({"user_declared", "document_derived"})
VALID_INCOME_BASES = frozenset({"cash_receipts_after_source_withholding"})
VALID_US_PERSON_STATUSES = frozenset({"us_person", "not_us_person", "unknown"})
VALID_US_FILING_STATUSES = frozenset(
    {"single", "married_joint", "married_separate", "other", "unknown"}
)
VALID_US_FILING_RESIDENCES = frozenset({"inside_us", "outside_us", "unknown"})


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FamilyMemberProtectionProfile(Base):
    """Confirmações de completude por pessoa; ausência não equivale a zero."""

    __tablename__ = "family_member_protection_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_member_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    economic_dependents_complete_as_of: Mapped[Optional[date]] = mapped_column(Date)
    debt_inventory_complete_as_of: Mapped[Optional[date]] = mapped_column(Date)
    life_policy_inventory_complete_as_of: Mapped[Optional[date]] = mapped_column(Date)
    disability_policy_inventory_complete_as_of: Mapped[Optional[date]] = mapped_column(Date)
    estate_inventory_complete_as_of: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "family_member_id", name="uq_member_protection_profile_ws_member"
        ),
    )


class EconomicDependency(Base):
    """Relação declarada entre dependente e provedor econômico."""

    __tablename__ = "economic_dependencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dependent_family_member_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False
    )
    provider_family_member_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    support_monthly_brl_cents: Mapped[Optional[int]] = mapped_column(BigInteger)
    support_share_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    dependency_end_date: Mapped[Optional[date]] = mapped_column(Date)
    durable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    __table_args__ = (
        CheckConstraint("status IN ('yes','no','unknown')", name="chk_dependency_status"),
        CheckConstraint(
            "source_kind IN ('user_declared','document_derived')",
            name="chk_dependency_source_kind",
        ),
        CheckConstraint(
            "dependent_family_member_id <> provider_family_member_id",
            name="chk_dependency_distinct_members",
        ),
        CheckConstraint(
            "support_monthly_brl_cents IS NULL OR support_monthly_brl_cents >= 0",
            name="chk_dependency_support_nonnegative",
        ),
        CheckConstraint(
            "support_share_pct IS NULL OR (support_share_pct >= 0 AND support_share_pct <= 100)",
            name="chk_dependency_share_range",
        ),
        UniqueConstraint(
            "workspace_id",
            "dependent_family_member_id",
            "provider_family_member_id",
            "as_of_date",
            name="uq_dependency_ws_pair_asof",
        ),
        Index("ix_dependency_ws_provider", "workspace_id", "provider_family_member_id"),
    )


class ProtectionIncomeDeclaration(Base):
    """Renda líquida recorrente por membro e janela fechada."""

    __tablename__ = "protection_income_declarations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_member_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False
    )
    active_net_annual_brl_cents: Mapped[Optional[int]] = mapped_column(BigInteger)
    passive_net_annual_brl_cents: Mapped[Optional[int]] = mapped_column(BigInteger)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    observed_months: Mapped[int] = mapped_column(Integer, nullable=False)
    basis: Mapped[str] = mapped_column(String(64), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "active_net_annual_brl_cents IS NULL OR active_net_annual_brl_cents >= 0",
            name="chk_protection_income_active_nonnegative",
        ),
        CheckConstraint(
            "passive_net_annual_brl_cents IS NULL OR passive_net_annual_brl_cents >= 0",
            name="chk_protection_income_passive_nonnegative",
        ),
        CheckConstraint("period_start <= period_end", name="chk_protection_income_period"),
        CheckConstraint(
            "observed_months >= 1 AND observed_months <= 12",
            name="chk_protection_income_months",
        ),
        CheckConstraint(
            "basis = 'cash_receipts_after_source_withholding'",
            name="chk_protection_income_basis",
        ),
        CheckConstraint(
            "source_kind IN ('user_declared','document_derived')",
            name="chk_protection_income_source_kind",
        ),
        UniqueConstraint(
            "workspace_id", "family_member_id", "as_of_date", name="uq_income_ws_member_asof"
        ),
        Index("ix_income_ws_asof", "workspace_id", "as_of_date"),
    )


class FamilyMemberTaxProfile(Base):
    """Perfil fiscal person-scoped; NULL é não declarado, nunca false."""

    __tablename__ = "family_member_tax_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_member_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    br_succession_uf: Mapped[Optional[str]] = mapped_column(String(2))
    us_person_status: Mapped[Optional[str]] = mapped_column(String(20))
    us_filing_status: Mapped[Optional[str]] = mapped_column(String(20))
    us_filing_residence: Mapped[Optional[str]] = mapped_column(String(16))
    foreign_financial_accounts_max_usd_cents: Mapped[Optional[int]] = mapped_column(BigInteger)
    specified_foreign_assets_end_usd_cents: Mapped[Optional[int]] = mapped_column(BigInteger)
    specified_foreign_assets_max_usd_cents: Mapped[Optional[int]] = mapped_column(BigInteger)
    us_situs_estate_assets_usd_cents: Mapped[Optional[int]] = mapped_column(BigInteger)
    estate_tax_treaty_code: Mapped[Optional[str]] = mapped_column(String(32))
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "us_person_status IS NULL OR us_person_status IN "
            "('us_person','not_us_person','unknown')",
            name="chk_tax_profile_us_person_status",
        ),
        CheckConstraint(
            "us_filing_status IS NULL OR us_filing_status IN "
            "('single','married_joint','married_separate','other','unknown')",
            name="chk_tax_profile_filing_status",
        ),
        CheckConstraint(
            "us_filing_residence IS NULL OR us_filing_residence IN "
            "('inside_us','outside_us','unknown')",
            name="chk_tax_profile_filing_residence",
        ),
        CheckConstraint(
            "source_kind IN ('user_declared','document_derived')",
            name="chk_tax_profile_source_kind",
        ),
        CheckConstraint(
            "foreign_financial_accounts_max_usd_cents IS NULL OR "
            "foreign_financial_accounts_max_usd_cents >= 0",
            name="chk_tax_profile_fbar_nonnegative",
        ),
        CheckConstraint(
            "specified_foreign_assets_end_usd_cents IS NULL OR "
            "specified_foreign_assets_end_usd_cents >= 0",
            name="chk_tax_profile_fatca_end_nonnegative",
        ),
        CheckConstraint(
            "specified_foreign_assets_max_usd_cents IS NULL OR "
            "specified_foreign_assets_max_usd_cents >= 0",
            name="chk_tax_profile_fatca_max_nonnegative",
        ),
        CheckConstraint(
            "us_situs_estate_assets_usd_cents IS NULL OR us_situs_estate_assets_usd_cents >= 0",
            name="chk_tax_profile_estate_nonnegative",
        ),
        UniqueConstraint("workspace_id", "family_member_id", name="uq_tax_profile_ws_member"),
    )


__all__ = [
    "EconomicDependency",
    "FamilyMemberProtectionProfile",
    "FamilyMemberTaxProfile",
    "ProtectionIncomeDeclaration",
    "VALID_DEPENDENCY_STATUSES",
    "VALID_INCOME_BASES",
    "VALID_PROTECTION_SOURCE_KINDS",
    "VALID_US_FILING_RESIDENCES",
    "VALID_US_FILING_STATUSES",
    "VALID_US_PERSON_STATUSES",
]
