"""Document model — uploaded financial documents with classification metadata."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    unlocking = "unlocking"
    classifying = "classifying"
    ready = "ready"
    needs_password = "needs_password"
    processing = "processing"
    processed = "processed"
    error = "error"


class DocumentType(str, enum.Enum):
    bank_statement = "bank_statement"
    credit_card_bill = "credit_card_bill"
    investment_report = "investment_report"
    irpf = "irpf"
    e1_members_json = "e1_members_json"
    e1_5_baseline_json = "e1_5_baseline_json"
    other = "other"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=True)
    doc_type: Mapped[str] = mapped_column(
        Enum(DocumentType), nullable=True, default=DocumentType.other
    )
    bank_code: Mapped[str] = mapped_column(String(50), nullable=True)
    period: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(DocumentStatus), nullable=False, default=DocumentStatus.uploaded, index=True
    )
    classification_meta: Mapped[dict] = mapped_column(JSON, nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workspace = relationship("Workspace", back_populates="documents")
