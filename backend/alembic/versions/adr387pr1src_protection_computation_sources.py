"""ADR-387: fontes relacionais do ProtectionComputationSnapshotV1.

Revision ID: adr387pr1src
Revises: adr384cnpjseed
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr387pr1src"
down_revision: Union[str, Sequence[str], None] = "adr384cnpjseed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SOURCE_KIND = "source_kind IN ('user_declared','document_derived')"


def _ws_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE")


def _member_fk(column: str = "family_member_id") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], ["family_members.id"], ondelete="CASCADE")


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def _id_ws_member() -> tuple[sa.Column, sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("family_member_id", sa.String(36), nullable=False),
    )


def _cents_or_null(column: str, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        f"{column} IS NULL OR {column} >= 0",
        name=name,
    )


def _profile_columns() -> tuple:
    return (
        *_id_ws_member(),
        sa.Column("economic_dependents_complete_as_of", sa.Date()),
        sa.Column("debt_inventory_complete_as_of", sa.Date()),
        sa.Column("life_policy_inventory_complete_as_of", sa.Date()),
        sa.Column("disability_policy_inventory_complete_as_of", sa.Date()),
        sa.Column("estate_inventory_complete_as_of", sa.Date()),
        *_timestamps(),
    )


def _dependency_columns() -> tuple:
    return (
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("dependent_family_member_id", sa.String(36), nullable=False),
        sa.Column("provider_family_member_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("support_monthly_brl_cents", sa.BigInteger()),
        sa.Column("support_share_pct", sa.Numeric(5, 2)),
        sa.Column("dependency_end_date", sa.Date()),
        sa.Column("durable", sa.Boolean(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("source_kind", sa.String(24), nullable=False),
        *_timestamps(),
    )


def _dependency_checks() -> tuple:
    return (
        sa.CheckConstraint("status IN ('yes','no','unknown')", name="chk_dependency_status"),
        sa.CheckConstraint(_SOURCE_KIND, name="chk_dependency_source_kind"),
        sa.CheckConstraint(
            "dependent_family_member_id <> provider_family_member_id",
            name="chk_dependency_distinct_members",
        ),
        _cents_or_null("support_monthly_brl_cents", "chk_dependency_support_nonnegative"),
        sa.CheckConstraint(
            "support_share_pct IS NULL OR (support_share_pct >= 0 AND support_share_pct <= 100)",
            name="chk_dependency_share_range",
        ),
    )


def _income_columns() -> tuple:
    return (
        *_id_ws_member(),
        sa.Column("active_net_annual_brl_cents", sa.BigInteger()),
        sa.Column("passive_net_annual_brl_cents", sa.BigInteger()),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("observed_months", sa.Integer(), nullable=False),
        sa.Column("basis", sa.String(64), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("source_kind", sa.String(24), nullable=False),
        *_timestamps(),
    )


def _income_checks() -> tuple:
    return (
        _cents_or_null("active_net_annual_brl_cents", "chk_protection_income_active_nonnegative"),
        _cents_or_null("passive_net_annual_brl_cents", "chk_protection_income_passive_nonnegative"),
        sa.CheckConstraint("period_start <= period_end", name="chk_protection_income_period"),
        sa.CheckConstraint(
            "observed_months >= 1 AND observed_months <= 12",
            name="chk_protection_income_months",
        ),
        sa.CheckConstraint(
            "basis = 'cash_receipts_after_source_withholding'",
            name="chk_protection_income_basis",
        ),
        sa.CheckConstraint(_SOURCE_KIND, name="chk_protection_income_source_kind"),
    )


def _tax_columns() -> tuple:
    return (
        *_id_ws_member(),
        sa.Column("br_succession_uf", sa.String(2)),
        sa.Column("us_person_status", sa.String(20)),
        sa.Column("us_filing_status", sa.String(20)),
        sa.Column("us_filing_residence", sa.String(16)),
        sa.Column("foreign_financial_accounts_max_usd_cents", sa.BigInteger()),
        sa.Column("specified_foreign_assets_end_usd_cents", sa.BigInteger()),
        sa.Column("specified_foreign_assets_max_usd_cents", sa.BigInteger()),
        sa.Column("us_situs_estate_assets_usd_cents", sa.BigInteger()),
        sa.Column("estate_tax_treaty_code", sa.String(32)),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("source_kind", sa.String(24), nullable=False),
        *_timestamps(),
    )


def _tax_status_checks() -> tuple:
    return (
        sa.CheckConstraint(
            "us_person_status IS NULL OR us_person_status IN "
            "('us_person','not_us_person','unknown')",
            name="chk_tax_profile_us_person_status",
        ),
        sa.CheckConstraint(
            "us_filing_status IS NULL OR us_filing_status IN "
            "('single','married_joint','married_separate','other','unknown')",
            name="chk_tax_profile_filing_status",
        ),
        sa.CheckConstraint(
            "us_filing_residence IS NULL OR us_filing_residence IN "
            "('inside_us','outside_us','unknown')",
            name="chk_tax_profile_filing_residence",
        ),
        sa.CheckConstraint(_SOURCE_KIND, name="chk_tax_profile_source_kind"),
    )


def _tax_amount_checks() -> tuple:
    return (
        _cents_or_null(
            "foreign_financial_accounts_max_usd_cents", "chk_tax_profile_fbar_nonnegative"
        ),
        _cents_or_null(
            "specified_foreign_assets_end_usd_cents", "chk_tax_profile_fatca_end_nonnegative"
        ),
        _cents_or_null(
            "specified_foreign_assets_max_usd_cents", "chk_tax_profile_fatca_max_nonnegative"
        ),
        _cents_or_null("us_situs_estate_assets_usd_cents", "chk_tax_profile_estate_nonnegative"),
    )


def _fiscal_rule_columns() -> tuple:
    return (
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_code", sa.String(24), nullable=False),
        sa.Column("jurisdiction_code", sa.String(24), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _fiscal_rule_constraints() -> tuple:
    return (
        sa.CheckConstraint(
            "rule_code IN ('BR_ITCMD','US_FBAR','US_FATCA','US_ESTATE_NRA')",
            name="chk_fiscal_rule_code",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_fiscal_rule_period",
        ),
        sa.UniqueConstraint(
            "rule_code",
            "jurisdiction_code",
            "effective_from",
            name="uq_fiscal_rule_code_jurisdiction_from",
        ),
    )


def _add_protection_columns(batch_op) -> None:
    batch_op.add_column(sa.Column("insured_family_member_id", sa.String(36)))
    batch_op.add_column(sa.Column("benefit_mode", sa.String(16)))
    batch_op.add_column(sa.Column("benefit_monthly_brl_cents", sa.BigInteger()))
    batch_op.create_foreign_key(
        "fk_protections_insured_family_member_id",
        "family_members",
        ["insured_family_member_id"],
        ["id"],
        ondelete="SET NULL",
    )
    batch_op.create_check_constraint(
        "chk_protection_benefit_mode",
        "benefit_mode IS NULL OR benefit_mode IN ('lump_sum','monthly_income')",
    )
    batch_op.create_check_constraint(
        "chk_protection_monthly_benefit_nonnegative",
        "benefit_monthly_brl_cents IS NULL OR benefit_monthly_brl_cents >= 0",
    )


def _add_protection_benefit_columns() -> None:
    with op.batch_alter_table("protections") as batch_op:
        _add_protection_columns(batch_op)
    op.create_index(
        "ix_protections_ws_insured",
        "protections",
        ["workspace_id", "insured_family_member_id"],
    )


def _create_member_protection_profiles() -> None:
    op.create_table(
        "family_member_protection_profiles",
        *_profile_columns(),
        _ws_fk(),
        _member_fk(),
        sa.UniqueConstraint(
            "workspace_id", "family_member_id", name="uq_member_protection_profile_ws_member"
        ),
        sa.UniqueConstraint("family_member_id"),
    )
    op.create_index(
        "ix_family_member_protection_profiles_workspace_id",
        "family_member_protection_profiles",
        ["workspace_id"],
    )


def _dependency_unique() -> sa.UniqueConstraint:
    return sa.UniqueConstraint(
        "workspace_id",
        "dependent_family_member_id",
        "provider_family_member_id",
        "as_of_date",
        name="uq_dependency_ws_pair_asof",
    )


def _create_economic_dependencies() -> None:
    op.create_table(
        "economic_dependencies",
        *_dependency_columns(),
        *_dependency_checks(),
        _ws_fk(),
        _member_fk("dependent_family_member_id"),
        _member_fk("provider_family_member_id"),
        _dependency_unique(),
    )
    op.create_index(
        "ix_economic_dependencies_workspace_id", "economic_dependencies", ["workspace_id"]
    )
    op.create_index(
        "ix_dependency_ws_provider",
        "economic_dependencies",
        ["workspace_id", "provider_family_member_id"],
    )


def _create_income_declarations() -> None:
    unique = sa.UniqueConstraint(
        "workspace_id", "family_member_id", "as_of_date", name="uq_income_ws_member_asof"
    )
    op.create_table(
        "protection_income_declarations",
        *_income_columns(),
        *_income_checks(),
        _ws_fk(),
        _member_fk(),
        unique,
    )
    op.create_index(
        "ix_protection_income_declarations_workspace_id",
        "protection_income_declarations",
        ["workspace_id"],
    )
    op.create_index(
        "ix_income_ws_asof", "protection_income_declarations", ["workspace_id", "as_of_date"]
    )


def _create_tax_profiles() -> None:
    op.create_table(
        "family_member_tax_profiles",
        *_tax_columns(),
        *_tax_status_checks(),
        *_tax_amount_checks(),
        _ws_fk(),
        _member_fk(),
        sa.UniqueConstraint("workspace_id", "family_member_id", name="uq_tax_profile_ws_member"),
        sa.UniqueConstraint("family_member_id"),
    )
    op.create_index(
        "ix_family_member_tax_profiles_workspace_id",
        "family_member_tax_profiles",
        ["workspace_id"],
    )


def _create_fiscal_rule_sets() -> None:
    op.create_table("fiscal_rule_sets", *_fiscal_rule_columns(), *_fiscal_rule_constraints())
    op.create_index(
        "ix_fiscal_rule_lookup",
        "fiscal_rule_sets",
        ["rule_code", "jurisdiction_code", "effective_from"],
    )


def upgrade() -> None:
    _add_protection_benefit_columns()
    _create_member_protection_profiles()
    _create_economic_dependencies()
    _create_income_declarations()
    _create_tax_profiles()
    _create_fiscal_rule_sets()


def _drop_protection_benefit_columns(batch_op) -> None:
    batch_op.drop_constraint("chk_protection_monthly_benefit_nonnegative", type_="check")
    batch_op.drop_constraint("chk_protection_benefit_mode", type_="check")
    batch_op.drop_constraint("fk_protections_insured_family_member_id", type_="foreignkey")
    batch_op.drop_column("benefit_monthly_brl_cents")
    batch_op.drop_column("benefit_mode")
    batch_op.drop_column("insured_family_member_id")


def _drop_income_and_tax() -> None:
    op.drop_index(
        "ix_family_member_tax_profiles_workspace_id",
        table_name="family_member_tax_profiles",
    )
    op.drop_table("family_member_tax_profiles")
    op.drop_index("ix_income_ws_asof", table_name="protection_income_declarations")
    op.drop_index(
        "ix_protection_income_declarations_workspace_id",
        table_name="protection_income_declarations",
    )
    op.drop_table("protection_income_declarations")


def _drop_dependency_and_profile() -> None:
    op.drop_index("ix_dependency_ws_provider", table_name="economic_dependencies")
    op.drop_index("ix_economic_dependencies_workspace_id", table_name="economic_dependencies")
    op.drop_table("economic_dependencies")
    op.drop_index(
        "ix_family_member_protection_profiles_workspace_id",
        table_name="family_member_protection_profiles",
    )
    op.drop_table("family_member_protection_profiles")


def downgrade() -> None:
    op.drop_table("fiscal_rule_sets")
    _drop_income_and_tax()
    _drop_dependency_and_profile()
    op.drop_index("ix_protections_ws_insured", table_name="protections")
    with op.batch_alter_table("protections") as batch_op:
        _drop_protection_benefit_columns(batch_op)
