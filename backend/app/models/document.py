"""Document model — uploaded financial documents with classification metadata."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
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
    # Classification quality — filled by DocumentProcessor's content-first classifier
    classification_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0", index=True
    )
    # Fuzzy dedupe pointer — set when another doc in the same workspace has the
    # same (doc_type, bank_code, period) but a different content_hash. Does not
    # block the upload; UI surfaces it for user review.
    # Soft reference (no FK constraint) to keep the migration compatible with
    # alembic's offline --sql mode on SQLite (see ADR in the migration).
    possible_duplicate_of_id: Mapped[str] = mapped_column(
        String(36), nullable=True, index=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # Last pipeline run that completed successfully — paired with E2 extract check
    pipeline_last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pipeline_e2_extract_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    workspace = relationship("Workspace", back_populates="documents")
