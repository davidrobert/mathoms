"""DataExportRequest — fila assíncrona de export LGPD (Art. 18, V — portabilidade)."""

# Estados: pending → processing → ready → (downloaded | expired | failed).
# Worker em backend.app.tasks.lgpd_export.process_data_export. Conteúdo do
# tar.gz em storage/lgpd_exports/<request_id>.tar.gz; só metadata aqui.

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class DataExportRequestStatus:
    """Valores aceitos em `DataExportRequest.status` (não enum — SQLite)."""

    pending = "pending"
    processing = "processing"
    ready = "ready"
    downloaded = "downloaded"
    expired = "expired"
    failed = "failed"


VALID_DATA_EXPORT_STATUSES = frozenset(
    {
        DataExportRequestStatus.pending,
        DataExportRequestStatus.processing,
        DataExportRequestStatus.ready,
        DataExportRequestStatus.downloaded,
        DataExportRequestStatus.expired,
        DataExportRequestStatus.failed,
    }
)


class DataExportRequest(Base):
    __tablename__ = "data_export_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=DataExportRequestStatus.pending,
        server_default=DataExportRequestStatus.pending,
        index=True,
    )
    download_token: Mapped[Optional[str]] = mapped_column(String(96), nullable=True, unique=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
