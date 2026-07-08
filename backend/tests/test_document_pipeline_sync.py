"""Tests for pipeline E2 sync — ready → processed after a completed run."""

from datetime import datetime, timezone
from pathlib import Path

from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.services.pipeline.document_pipeline_sync import apply_pipeline_e2_sync_to_documents


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


def test_apply_pipeline_e2_sync_irpf_uses_db_fallback_when_disk_missing(tmp_path: Path) -> None:
    """DBArtifactStore mode: E1.5 escreve só no DB. Sync deve consultar DB
    em vez de marcar `pipeline_e2_extract_ok=False` (que produz badge
    "Sem extrato" na UI mesmo com extract presente)."""
    from unittest.mock import MagicMock, patch

    when = datetime(2026, 4, 23, 18, 0, tzinfo=timezone.utc)
    doc = Document(
        workspace_id="ws-1",
        original_name="receitafederal_irpfdeclaracao_2024.pdf",
        stored_path="data/income_tax_br/receitafederal_irpfdeclaracao_2024-0_original.pdf",
        status=DocumentStatus.ready,
        doc_type=DocumentType.irpf,
        file_size_bytes=1,
    )
    (tmp_path / "processed" / "E2_extracts").mkdir(parents=True)

    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = MagicMock()  # artifact exists
    with patch(
        "backend.app.services.pipeline.document_pipeline_sync.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        apply_pipeline_e2_sync_to_documents([doc], tmp_path, when, db=MagicMock())

    assert doc.pipeline_e2_extract_ok is True
    assert doc.status == DocumentStatus.processed
    fake_repo.get_latest_for_workspace.assert_called_once_with(
        "ws-1", stage="E1.5a", artifact_key="receitafederal_irpfdeclaracao_2024"
    )


def test_apply_pipeline_e2_sync_irpf_false_when_neither_disk_nor_db(tmp_path: Path) -> None:
    from unittest.mock import MagicMock, patch

    when = datetime(2026, 4, 23, 18, 0, tzinfo=timezone.utc)
    doc = Document(
        workspace_id="ws-1",
        original_name="receitafederal_irpfdeclaracao_2024.pdf",
        stored_path="data/income_tax_br/receitafederal_irpfdeclaracao_2024-0_original.pdf",
        status=DocumentStatus.ready,
        doc_type=DocumentType.irpf,
        file_size_bytes=1,
    )

    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = None
    with patch(
        "backend.app.services.pipeline.document_pipeline_sync.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        apply_pipeline_e2_sync_to_documents([doc], tmp_path, when, db=MagicMock())

    assert doc.pipeline_e2_extract_ok is False


def _make_e2_doc(stem: str, doc_type: DocumentType) -> Document:
    return Document(
        workspace_id="ws-1",
        original_name=f"{stem}.pdf",
        stored_path=f"data/{stem}-0_original.pdf",
        status=DocumentStatus.ready,
        doc_type=doc_type,
        file_size_bytes=1,
    )


def test_apply_pipeline_e2_sync_e2_uses_db_fallback_when_disk_missing(tmp_path: Path) -> None:
    """DBArtifactStore mode: E2 sem disco → consulta DB; flag fica True."""
    from unittest.mock import MagicMock, patch

    when = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)
    doc = _make_e2_doc("c6bank_extratoconta_202604", DocumentType.bank_statement)
    (tmp_path / "processed" / "E2_extracts").mkdir(parents=True)
    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.side_effect = [MagicMock(), None, None]
    with patch(
        "backend.app.services.pipeline.document_pipeline_sync.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        apply_pipeline_e2_sync_to_documents([doc], tmp_path, when, db=MagicMock())
    assert doc.pipeline_e2_extract_ok is True
    assert doc.status == DocumentStatus.processed
    fake_repo.get_latest_for_workspace.assert_any_call(
        "ws-1", stage="extract_statements", artifact_key="c6bank_extratoconta_202604"
    )


def test_apply_pipeline_e2_sync_e2_false_when_neither_disk_nor_db(tmp_path: Path) -> None:
    from unittest.mock import MagicMock, patch

    when = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)
    doc = _make_e2_doc("itau_faturacc_202604", DocumentType.credit_card_bill)
    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = None
    with patch(
        "backend.app.services.pipeline.document_pipeline_sync.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        apply_pipeline_e2_sync_to_documents([doc], tmp_path, when, db=MagicMock())
    assert doc.pipeline_e2_extract_ok is False


def _flagged_doc(stored_path: str, doc_type: DocumentType) -> Document:
    return Document(
        workspace_id="ws-1",
        original_name=Path(stored_path).name,
        stored_path=stored_path,
        status=DocumentStatus.ready,
        doc_type=doc_type,
        file_size_bytes=1,
        needs_review=True,
        classification_confidence=0.6,
    )


_WHEN = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)


def test_apply_pipeline_e2_sync_clears_needs_review_when_e2_extracted(tmp_path: Path) -> None:
    """E2 extract bem-sucedido confirma classificação — limpa flag 'incerta'."""
    doc = _flagged_doc("data/bank/foo-0_original.pdf", DocumentType.bank_statement)
    e2 = tmp_path / "processed" / "E2_extracts"
    e2.mkdir(parents=True)
    (e2 / "foo-2_extract.json").write_text("{}")
    apply_pipeline_e2_sync_to_documents([doc], tmp_path, _WHEN)
    assert doc.pipeline_e2_extract_ok is True
    assert doc.needs_review is False


def test_apply_pipeline_e2_sync_keeps_needs_review_when_no_extract(tmp_path: Path) -> None:
    """Sem extract artefato, o flag de incerteza permanece — UI segue avisando."""
    doc = _flagged_doc("data/bank/x-0_original.pdf", DocumentType.bank_statement)
    (tmp_path / "processed" / "E2_extracts").mkdir(parents=True)
    apply_pipeline_e2_sync_to_documents([doc], tmp_path, _WHEN)
    assert doc.pipeline_e2_extract_ok is False
    assert doc.needs_review is True


def test_apply_pipeline_e2_sync_clears_needs_review_for_irpf_e15a(tmp_path: Path) -> None:
    """IRPF com E1.5a artefato (DB) → limpa needs_review do upload-time."""
    from unittest.mock import MagicMock, patch

    doc = _flagged_doc(
        "data/income_tax_br/receitafederal_irpfrecibo_2025-0_original.pdf",
        DocumentType.irpf,
    )
    (tmp_path / "processed" / "E2_extracts").mkdir(parents=True)
    fake_repo = MagicMock()
    fake_repo.get_latest_for_workspace.return_value = MagicMock()
    with patch(
        "backend.app.services.pipeline.document_pipeline_sync.PipelineArtifactRepository",
        return_value=fake_repo,
    ):
        apply_pipeline_e2_sync_to_documents([doc], tmp_path, _WHEN, db=MagicMock())
    assert doc.pipeline_e2_extract_ok is True
    assert doc.needs_review is False


def test_apply_pipeline_e2_sync_investment_report_none_when_no_extract(tmp_path: Path) -> None:
    """investment_report sem extract → None ("Processado"), não False ("Sem extrato")."""
    when = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)
    doc = Document(
        workspace_id="ws-1",
        original_name="itau_investimentosposicao_2026-0_original.xls",
        stored_path="data/financial_statements/itau_investimentosposicao_2026-0_original.xls",
        status=DocumentStatus.ready,
        doc_type=DocumentType.investment_report,
        file_size_bytes=1,
    )
    (tmp_path / "processed" / "E2_extracts").mkdir(parents=True)
    apply_pipeline_e2_sync_to_documents([doc], tmp_path, when)
    assert doc.pipeline_e2_extract_ok is None
    assert doc.status == DocumentStatus.processed


def test_apply_pipeline_e2_sync_investment_report_true_when_extract_present(tmp_path: Path) -> None:
    """investment_report com extract artefato → True ("Extraído")."""
    when = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)
    doc = Document(
        workspace_id="ws-1",
        original_name="itau_investimentosposicao_2026-0_original.xls",
        stored_path="data/financial_statements/itau_investimentosposicao_2026-0_original.xls",
        status=DocumentStatus.ready,
        doc_type=DocumentType.investment_report,
        file_size_bytes=1,
    )
    e2 = tmp_path / "processed" / "E2_extracts"
    e2.mkdir(parents=True)
    (e2 / "itau_investimentosposicao_2026-2_extract.json").write_text("{}")

    apply_pipeline_e2_sync_to_documents([doc], tmp_path, when)
    assert doc.pipeline_e2_extract_ok is True


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
