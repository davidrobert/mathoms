"""DataSource — origem canônica plugável de artefatos (ADR-278); materializa o
``SourceRef`` de domínio no DB. Registro de fonte (adapter), não dado de usuário — daí a
sentinela ``''`` em ``institution_code``/``external_account_ref`` (NULL quebraria o unique
no Postgres). Folha fina continua em ``pipeline_artifacts.document_id``; isto é a fonte coarse."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class DataSource(Base):
    __tablename__ = "data_source"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "kind",
            "institution_code",
            "external_account_ref",
            name="uq_data_source_natural_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    institution_code: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="", default=""
    )
    external_account_ref: Mapped[str] = mapped_column(
        String(128), nullable=False, server_default="", default=""
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    workspace = relationship("Workspace")
