"""Tests for pipeline E2 sync — ready → processed after a completed run."""

from datetime import datetime, timezone
from pathlib import Path

from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.services.document_pipeline_sync import apply_pipeline_e2_sync_to_documents


def test_apply_pipeline_e2_sync_promotes_ready_to_processed(tmp_path: Path) -> None:
    when = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    doc = Document(
        workspace_id="ws-1",
        original_name="extrato.pdf",
        stored_path="data/bank/foo-0_original.pdf",
        status=DocumentStatus.ready,
        doc_type=DocumentType.bank_statement,
        file_size_bytes=1,
    )
    e2 = tmp_path / "processed" / "E2_extracts"
    e2.mkdir(parents=True)
    (e2 / "foo-2_extract.json").write_text("{}")

    apply_pipeline_e2_sync_to_documents([doc], tmp_path, when)

    assert doc.status == DocumentStatus.processed
    assert doc.pipeline_last_run_at == when
    assert doc.pipeline_e2_extract_ok is True


def test_apply_pipeline_e2_sync_keeps_processed(tmp_path: Path) -> None:
    when = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    doc = Document(
        workspace_id="ws-1",
        original_name="x.pdf",
        stored_path="data/bank/x-0_original.pdf",
        status=DocumentStatus.processed,
        doc_type=DocumentType.bank_statement,
        file_size_bytes=1,
    )
    apply_pipeline_e2_sync_to_documents([doc], tmp_path, when)
    assert doc.status == DocumentStatus.processed


def test_apply_pipeline_e2_sync_skips_needs_password(tmp_path: Path) -> None:
    when = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    doc = Document(
        workspace_id="ws-1",
        original_name="locked.pdf",
        stored_path="inbox/locked-0_original.pdf",
        status=DocumentStatus.needs_password,
        doc_type=DocumentType.bank_statement,
        file_size_bytes=1,
    )
    apply_pipeline_e2_sync_to_documents([doc], tmp_path, when)
    assert doc.status == DocumentStatus.needs_password
