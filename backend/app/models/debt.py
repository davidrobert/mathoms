"""Debt aggregate — passivo persistido por workspace (ADR-227 §D1)."""

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
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

# Enum `tipo` (ADR-227 §D1). 6 valores brasileiros; `cartao_rotativo`
# separado de `rotativo` desde V1 — cartão tem comportamento próprio em
# E5 (categorização Cerbasi anti-rotativo). Source of truth aqui; CHECK
# constraint na migration replica os valores.
DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO = "financiamento_imobiliario"
DEBT_TIPO_CONSIGNADO = "consignado"
DEBT_TIPO_CDC = "cdc"
DEBT_TIPO_CARTAO_ROTATIVO = "cartao_rotativo"
DEBT_TIPO_ROTATIVO = "rotativo"
DEBT_TIPO_OUTRO = "outro"

VALID_DEBT_TIPOS = (
    DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO,
    DEBT_TIPO_CONSIGNADO,
    DEBT_TIPO_CDC,
    DEBT_TIPO_CARTAO_ROTATIVO,
    DEBT_TIPO_ROTATIVO,
    DEBT_TIPO_OUTRO,
)

# Enum `source` (ADR-227 §D1). Distingue origem da row:
# - `baseline_irpf_migration` — extraído por backfill da Onda 2.
# - `user_declared` — usuário declarou via API/UI.
# - `open_banking_futuro` — placeholder para integração V2.
DEBT_SOURCE_BASELINE_IRPF_MIGRATION = "baseline_irpf_migration"
DEBT_SOURCE_USER_DECLARED = "user_declared"
DEBT_SOURCE_OPEN_BANKING_FUTURO = "open_banking_futuro"

VALID_DEBT_SOURCES = (
    DEBT_SOURCE_BASELINE_IRPF_MIGRATION,
    DEBT_SOURCE_USER_DECLARED,
    DEBT_SOURCE_OPEN_BANKING_FUTURO,
)


class Debt(Base):
    """Passivo persistido (ADR-227 §D1) — substitui ``total_dividas`` baseline; FK a property com RESTRICT impede órfão silencioso."""

    __tablename__ = "debt"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ("
            "'financiamento_imobiliario','consignado','cdc',"
            "'cartao_rotativo','rotativo','outro')",
            name="chk_debt_tipo",
        ),
        CheckConstraint(
            "source IN ('baseline_irpf_migration','user_declared','open_banking_futuro')",
            name="chk_debt_source",
        ),
        CheckConstraint(
            "percentual_atribuicao_imovel IS NULL "
            "OR (percentual_atribuicao_imovel > 0 "
            "AND percentual_atribuicao_imovel <= 100)",
            name="chk_debt_pct_atribuicao",
        ),
        CheckConstraint(
            "family_member_id IS NOT NULL OR property_id IS NOT NULL OR descricao IS NOT NULL",
            name="chk_debt_identity",
        ),
        Index("ix_debt_workspace", "workspace_id"),
        # Partial unique: idempotência do backfill de cutover (Onda 2).
        # Espelha `sqlite_where` + `postgresql_where` da migration.
        # Declarado aqui também porque tests usam Base.metadata.create_all
        # em vez de rodar Alembic (pattern ADR-215).
        Index(
            "uq_debt_migration_source",
            "workspace_id",
            "migration_source_key",
            unique=True,
            sqlite_where=text("source = 'baseline_irpf_migration'"),
            postgresql_where=text("source = 'baseline_irpf_migration'"),
        ),
        Index(
            "ix_debt_property",
            "property_id",
            sqlite_where=text("property_id IS NOT NULL"),
            postgresql_where=text("property_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    family_member_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    property_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("property_identity.id", ondelete="RESTRICT"),
        nullable=True,
    )
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    saldo_devedor_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parcela_mensal_cents: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    taxa_juros_aa: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    prazo_meses_restantes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    data_contratacao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    migration_source_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    needs_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    percentual_atribuicao_imovel: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


__all__ = [
    "Debt",
    "VALID_DEBT_TIPOS",
    "VALID_DEBT_SOURCES",
    "DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO",
    "DEBT_TIPO_CONSIGNADO",
    "DEBT_TIPO_CDC",
    "DEBT_TIPO_CARTAO_ROTATIVO",
    "DEBT_TIPO_ROTATIVO",
    "DEBT_TIPO_OUTRO",
    "DEBT_SOURCE_BASELINE_IRPF_MIGRATION",
    "DEBT_SOURCE_USER_DECLARED",
    "DEBT_SOURCE_OPEN_BANKING_FUTURO",
]
