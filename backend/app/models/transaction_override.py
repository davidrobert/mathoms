"""TransactionOverride — user corrections + ``source``/``rule_id``/``deleted_at`` (ADR-186/188 A12)."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

OVERRIDE_SOURCE_MANUAL: str = "manual"
OVERRIDE_SOURCE_RULE: str = "rule"
VALID_OVERRIDE_SOURCES: frozenset[str] = frozenset({OVERRIDE_SOURCE_MANUAL, OVERRIDE_SOURCE_RULE})


class TransactionOverride(Base):
    __tablename__ = "transaction_overrides"
    __table_args__ = (
        UniqueConstraint("workspace_id", "transaction_hash", name="uq_override_ws_hash"),
        # Partial unique race-protection (ADR-188 §D2) is enforced via a
        # partial index criada na migration a2b3c4d5e6f7 — não declarável
        # diretamente em __table_args__ porque SQLAlchemy não expressa
        # WHERE em UniqueConstraint. Documentado para descoberta.
        #
        # ADR-282: o match v2 usa o índice parcial composto
        # ``ix_txov_ws_natural_key`` (workspace_id, natural_key_hash) WHERE
        # natural_key_hash IS NOT NULL AND deleted_at IS NULL, criado na
        # migration adr282overridenk (migration-only, mesma razão do WHERE).
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_category: Mapped[str] = mapped_column(String(255), nullable=False)
    new_category: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OVERRIDE_SOURCE_MANUAL, server_default="manual"
    )
    rule_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("categorization_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # ADR-188 §D1 — soft-delete preserva histórico para consultor B2B2C.
    # Read-path E4 deve consumir via view ``transaction_overrides_active``
    # (filtra ``deleted_at IS NULL``).
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ADR-282 — identidade v2 unificada com o natural_key do pipeline.
    # ``transaction_hash`` (acima) é o legado ``generate_transaction_hash`` mantido
    # durante a janela de migração (dropado na M2 destrutiva). Nullable enquanto
    # nenhum read-path consome (flag ``override_natural_key_v2_enabled`` off).
    natural_key_hash: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    hash_version: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    # Snapshot dos inputs do hash — invariante ADR-282: a linha é re-hasheável
    # sozinha, sem replay de E4 (paga a dívida na raiz; habilita lineage reverso).
    tx_data: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    tx_banco: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tx_titular: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tx_tipo_conta: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tx_valor_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tx_moeda: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    tx_direction: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    tx_descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Órfão: ``natural_key_hash`` não pôde ser reancorado no E4 atual (backfill).
    # Quarentena — nunca drop (ADR-282 §política de órfão).
    orphaned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace", back_populates="transaction_overrides")
