"""ADR-227 Onda 1: agregado Debt + property_market_value (FU-3 Sprint A15).

Revision ID: adr227debt1
Revises: adr172heartbeat
Create Date: 2026-05-20

Persistência base do FU-3 ([[ADR-227]] §D1 + §D2). Duas tabelas novas
em revision única:

1. ``debt`` — agregado de passivo persistido. Substitui o ``total_dividas``
   agregado-por-membro do baseline IRPF. Suporta financiamento
   imobiliário (com FK opcional a property_identity), CDC, consignado,
   cartão rotativo, rotativo, outro. ``ON DELETE RESTRICT`` em
   ``property_id`` impede órfão silencioso (bug invisível em fintech —
   investivel_efetivo inflaria sem aviso após delete de property).

2. ``property_market_value`` — declaração versionada (append-only) de
   valor de mercado por imóvel. Substitui o uso de ``valor_brl`` IRPF
   (custo histórico) em cat_2 do calculator, quando declarado e ≤12m
   (TTL com banner, sem fallback automático — [[ADR-223]] §Riscos).

Sem mudança runtime: Onda 2 popula via backfill, Onda 3 consome via
resolver puro, Onda 4 expõe API. Calculator, EndividamentoAnalyzer,
RealEstateMetrics permanecem inalterados até Onda 3.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr227debt1"
down_revision: Union[str, Sequence[str], None] = "adr172heartbeat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VALID_DEBT_TIPOS = (
    "financiamento_imobiliario",
    "consignado",
    "cdc",
    "cartao_rotativo",
    "rotativo",
    "outro",
)
_VALID_DEBT_SOURCES = (
    "baseline_irpf_migration",
    "user_declared",
    "open_banking_futuro",
)
_VALID_PMV_SOURCES = (
    "user_declared",
    "avaliacao_terceiros",
    "cep_proxy_futuro",
)


def _quote_list(values: tuple[str, ...]) -> str:
    return ",".join(f"'{v}'" for v in values)


def upgrade() -> None:
    """Create debt + property_market_value with CHECK/UNIQUE/FK constraints."""
    # ────────────────────────────────────────────────────────────────────
    # 1) debt — agregado de passivo (ADR-227 §D1)
    # ────────────────────────────────────────────────────────────────────
    op.create_table(
        "debt",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "family_member_id",
            sa.String(length=36),
            sa.ForeignKey("family_members.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "property_id",
            sa.String(length=36),
            sa.ForeignKey("property_identity.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("saldo_devedor_cents", sa.BigInteger(), nullable=False),
        sa.Column("parcela_mensal_cents", sa.BigInteger(), nullable=True),
        sa.Column("taxa_juros_aa", sa.Numeric(5, 2), nullable=True),
        sa.Column("prazo_meses_restantes", sa.Integer(), nullable=True),
        sa.Column("data_contratacao", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("migration_source_key", sa.String(length=64), nullable=True),
        sa.Column(
            "needs_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "percentual_atribuicao_imovel",
            sa.Numeric(5, 2),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            f"tipo IN ({_quote_list(_VALID_DEBT_TIPOS)})",
            name="chk_debt_tipo",
        ),
        sa.CheckConstraint(
            f"source IN ({_quote_list(_VALID_DEBT_SOURCES)})",
            name="chk_debt_source",
        ),
        sa.CheckConstraint(
            "percentual_atribuicao_imovel IS NULL "
            "OR (percentual_atribuicao_imovel > 0 "
            "AND percentual_atribuicao_imovel <= 100)",
            name="chk_debt_pct_atribuicao",
        ),
        sa.CheckConstraint(
            "family_member_id IS NOT NULL OR property_id IS NOT NULL OR descricao IS NOT NULL",
            name="chk_debt_identity",
        ),
    )
    op.create_index("ix_debt_workspace", "debt", ["workspace_id"])
    op.create_index(
        "ix_debt_property",
        "debt",
        ["property_id"],
        sqlite_where=sa.text("property_id IS NOT NULL"),
        postgresql_where=sa.text("property_id IS NOT NULL"),
    )
    # Partial unique p/ idempotência da migration de cutover (Onda 2):
    # re-run do backfill no-op por (workspace, member_key).
    op.create_index(
        "uq_debt_migration_source",
        "debt",
        ["workspace_id", "migration_source_key"],
        unique=True,
        sqlite_where=sa.text("source = 'baseline_irpf_migration'"),
        postgresql_where=sa.text("source = 'baseline_irpf_migration'"),
    )

    # ────────────────────────────────────────────────────────────────────
    # 2) property_market_value — declaração versionada (ADR-227 §D2)
    # ────────────────────────────────────────────────────────────────────
    op.create_table(
        "property_market_value",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "property_id",
            sa.String(length=36),
            sa.ForeignKey("property_identity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("valor_brl_cents", sa.BigInteger(), nullable=False),
        sa.Column("valuation_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "superseded_by_id",
            sa.String(length=36),
            sa.ForeignKey(
                "property_market_value.id",
                ondelete="SET NULL",
                use_alter=True,
                name="fk_pmv_superseded_by",
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "property_id",
            "valuation_date",
            name="uq_property_valuation_date",
        ),
        sa.CheckConstraint(
            f"source IN ({_quote_list(_VALID_PMV_SOURCES)})",
            name="chk_pmv_source",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="chk_pmv_confidence",
        ),
    )
    op.create_index(
        "idx_pmv_lookup",
        "property_market_value",
        ["workspace_id", "property_id", sa.text("valuation_date DESC")],
    )


def downgrade() -> None:
    """Drop both tables. Rows in flight are lost (sprint A15 cutover only)."""
    op.drop_index("idx_pmv_lookup", table_name="property_market_value")
    op.drop_table("property_market_value")

    op.drop_index("uq_debt_migration_source", table_name="debt")
    op.drop_index("ix_debt_property", table_name="debt")
    op.drop_index("ix_debt_workspace", table_name="debt")
    op.drop_table("debt")
