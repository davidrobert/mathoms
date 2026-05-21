"""Property identity + override models (ADR-215)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

# Enum de classification (espelhado em ADR-215). Source of truth aqui;
# CHECK constraint na migration replica os valores.
CLASSIFICATION_RESIDENCIA_PRINCIPAL = "residencia_principal"
CLASSIFICATION_USO_PESSOAL = "uso_pessoal"
CLASSIFICATION_LOCADO = "locado"
CLASSIFICATION_COMERCIAL = "comercial"
CLASSIFICATION_ESPECULACAO = "especulacao"
# ADR-235: nu-propriedade com usufruto vitalício de terceiro. Ativo no
# patrimônio mas zero fluxo e ilíquido por contrato civil até consolidação.
# Comporta-se como uso_pessoal nos filtros computacionais.
CLASSIFICATION_NU_PROPRIETARIO = "nu_proprietario"
CLASSIFICATION_DESCONHECIDO = "desconhecido"

VALID_CLASSIFICATIONS = (
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    CLASSIFICATION_USO_PESSOAL,
    CLASSIFICATION_LOCADO,
    CLASSIFICATION_COMERCIAL,
    CLASSIFICATION_ESPECULACAO,
    CLASSIFICATION_NU_PROPRIETARIO,
    CLASSIFICATION_DESCONHECIDO,
)

OVERRIDE_SOURCE_USER_MANUAL = "user_manual"
OVERRIDE_SOURCE_FUZZY_MATCH_ACCEPTED = "fuzzy_match_accepted"
OVERRIDE_SOURCE_MIGRATION_KEYWORD = "migration_keyword"

VALID_OVERRIDE_SOURCES = (
    OVERRIDE_SOURCE_USER_MANUAL,
    OVERRIDE_SOURCE_FUZZY_MATCH_ACCEPTED,
    OVERRIDE_SOURCE_MIGRATION_KEYWORD,
)

RESIDENCIA_STATUS_OWNED = "owned"
RESIDENCIA_STATUS_RENTED = "rented"
RESIDENCIA_STATUS_UNDECLARED = "undeclared"

VALID_RESIDENCIA_STATUSES = (
    RESIDENCIA_STATUS_OWNED,
    RESIDENCIA_STATUS_RENTED,
    RESIDENCIA_STATUS_UNDECLARED,
)


class PropertyIdentity(Base):
    """Identidade estável de imóvel cross-IRPFs (gerada por E1.5c consolidador)."""

    __tablename__ = "property_identity"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    titular_key: Mapped[str] = mapped_column(String(64), nullable=False)
    codigo_rfb: Mapped[str] = mapped_column(String(4), nullable=False)
    endereco_canonical: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_seen_year: Mapped[int] = mapped_column(Integer, nullable=False)
    descricao_sample: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    low_confidence: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    overrides = relationship(
        "WorkspacePropertyOverride",
        back_populates="property",
        cascade="all, delete-orphan",
    )


class WorkspacePropertyOverride(Base):
    """Override de classificação econômica por imóvel (ADR-215)."""

    __tablename__ = "workspace_property_overrides"
    __table_args__ = (
        UniqueConstraint("workspace_id", "property_id", name="uq_workspace_property"),
        CheckConstraint(
            "classification IN ("
            "'residencia_principal','uso_pessoal','locado',"
            "'comercial','especulacao','nu_proprietario','desconhecido')",
            name="chk_classification_enum",
        ),
        CheckConstraint(
            "override_source IN ('user_manual','fuzzy_match_accepted','migration_keyword')",
            name="chk_override_source_enum",
        ),
        # Partial unique: 1 residencia_principal por workspace. Espelha
        # `sqlite_where` + `postgresql_where` da migration (ADR-215).
        # Declarado aqui também porque tests usam ``Base.metadata.create_all``
        # em vez de rodar Alembic.
        Index(
            "uq_workspace_one_residencia_principal",
            "workspace_id",
            unique=True,
            sqlite_where=text("classification = 'residencia_principal'"),
            postgresql_where=text("classification = 'residencia_principal'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("property_identity.id", ondelete="CASCADE"),
        nullable=False,
    )
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    override_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OVERRIDE_SOURCE_USER_MANUAL
    )
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    property = relationship("PropertyIdentity", back_populates="overrides")


__all__ = [
    "PropertyIdentity",
    "WorkspacePropertyOverride",
    "VALID_CLASSIFICATIONS",
    "VALID_OVERRIDE_SOURCES",
    "VALID_RESIDENCIA_STATUSES",
    "CLASSIFICATION_RESIDENCIA_PRINCIPAL",
    "CLASSIFICATION_USO_PESSOAL",
    "CLASSIFICATION_LOCADO",
    "CLASSIFICATION_COMERCIAL",
    "CLASSIFICATION_ESPECULACAO",
    "CLASSIFICATION_NU_PROPRIETARIO",
    "CLASSIFICATION_DESCONHECIDO",
    "OVERRIDE_SOURCE_USER_MANUAL",
    "OVERRIDE_SOURCE_FUZZY_MATCH_ACCEPTED",
    "OVERRIDE_SOURCE_MIGRATION_KEYWORD",
    "RESIDENCIA_STATUS_OWNED",
    "RESIDENCIA_STATUS_RENTED",
    "RESIDENCIA_STATUS_UNDECLARED",
]
