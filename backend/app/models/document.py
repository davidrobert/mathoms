"""Document model — uploaded financial documents with classification metadata."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

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

    @classmethod
    def _missing_(cls, value: object) -> "DocumentStatus":
        """Fallback para valores legados ou corrompidos no banco.

        Impede que um status desconhecido (e.g. 'classified' de código
        anterior à state machine P1.1) derrube o endpoint GET /documents
        inteiro com LookupError. O documento aparece com status 'error'
        na UI, sinalizando que precisa de atenção sem bloquear os demais.
        """
        import logging
        logging.getLogger(__name__).warning(
            "DocumentStatus desconhecido '%s' lido do banco — tratado como 'error'", value
        )
        return cls.error


# Documentos elegíveis para pipeline / relatório: classificação OK (antes ou depois de um run).
DOCUMENT_CLASSIFIED_OK: frozenset[DocumentStatus] = frozenset(
    {
        DocumentStatus.ready,
        DocumentStatus.processed,
    }
)


# ─── State machine (P1.1) ───
# Map `from_status → {allowed target statuses}`. Same-status transitions are
# always allowed (idempotent). Rationale:
#   - uploaded: entry state, can move to any unlock/classify flow.
#   - unlocking/classifying/processing: transient in-progress states.
#   - needs_password: user intervention expected; can retry.
#   - ready: classified successfully; can be reprocessed or reclassified.
#   - processed: pipeline completed; can be rerun.
#   - error: recoverable via manual reclassify or retry-unlock.
_ALLOWED_TRANSITIONS: "dict[DocumentStatus, frozenset[DocumentStatus]]" = {
    DocumentStatus.uploaded: frozenset({
        DocumentStatus.unlocking, DocumentStatus.classifying,
        DocumentStatus.needs_password, DocumentStatus.error,
    }),
    DocumentStatus.unlocking: frozenset({
        DocumentStatus.classifying, DocumentStatus.needs_password,
        DocumentStatus.ready, DocumentStatus.error,
    }),
    DocumentStatus.classifying: frozenset({
        DocumentStatus.ready, DocumentStatus.needs_password, DocumentStatus.error,
    }),
    DocumentStatus.needs_password: frozenset({
        DocumentStatus.classifying, DocumentStatus.ready, DocumentStatus.error,
    }),
    DocumentStatus.ready: frozenset({
        DocumentStatus.processing,
        DocumentStatus.classifying,
        DocumentStatus.error,
        DocumentStatus.processed,
    }),
    DocumentStatus.processing: frozenset({
        DocumentStatus.processed, DocumentStatus.ready, DocumentStatus.error,
    }),
    DocumentStatus.processed: frozenset({
        DocumentStatus.processing, DocumentStatus.ready, DocumentStatus.error,
    }),
    DocumentStatus.error: frozenset({
        DocumentStatus.classifying, DocumentStatus.unlocking,
        DocumentStatus.ready, DocumentStatus.needs_password,
    }),
}


class InvalidDocumentStatusTransition(ValueError):
    """Raised when an invalid DocumentStatus transition is attempted."""

    def __init__(self, current: DocumentStatus, target: DocumentStatus):
        super().__init__(
            f"Invalid DocumentStatus transition: {current.value} → {target.value}"
        )
        self.current = current
        self.target = target


def is_valid_document_transition(
    current: DocumentStatus, target: DocumentStatus
) -> bool:
    """Return True iff `current → target` is allowed (same-state is idempotent)."""
    if current == target:
        return True
    return target in _ALLOWED_TRANSITIONS.get(current, frozenset())


def assert_document_transition(
    current: DocumentStatus, target: DocumentStatus
) -> None:
    """Raise InvalidDocumentStatusTransition if transition is not allowed."""
    if not is_valid_document_transition(current, target):
        raise InvalidDocumentStatusTransition(current, target)


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

    @validates("status")
    def _validate_status_transition(self, key, new_value):
        """Enforce the DocumentStatus state machine (P1.1).

        Runs on every attribute set. The initial `__init__` set sees
        `current` as None (no previous committed value) — in that case we
        skip the check (object creation is always allowed to set any status).
        """
        # Normalize: accept str or enum
        if isinstance(new_value, str) and not isinstance(new_value, DocumentStatus):
            try:
                new_value = DocumentStatus(new_value)
            except ValueError:
                raise InvalidDocumentStatusTransition(
                    current=DocumentStatus.uploaded,  # placeholder
                    target=DocumentStatus.error,
                ) from None

        current = getattr(self, "status", None)
        if current is None:
            # Initial assignment during construction; no previous state.
            return new_value

        if isinstance(current, str) and not isinstance(current, DocumentStatus):
            try:
                current = DocumentStatus(current)
            except ValueError:
                return new_value  # corrupt state; allow overwrite

        assert_document_transition(current, new_value)
        return new_value
