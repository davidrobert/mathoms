"""Use cases do agregado ``Document`` — testes puros (sem DB, sem LLM)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.document import (
    delete_document,
    get_document,
    list_duplicate_candidates,
    list_workspace_documents,
    reclassify_document,
    update_document_classification,
)
from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.schemas.dto.document import DocumentUpdateCommand
from backend.tests.fakes import (
    FakeClassificationService,
    FakeDocumentRepository,
)


def _doc(**overrides) -> Document:
    defaults = dict(
        workspace_id="ws-1",
        original_name="extrato.pdf",
        stored_path="inbox/extrato.pdf",
        doc_type=DocumentType.bank_statement,
        bank_code="itau",
        period="2026-04",
        status=DocumentStatus.ready,
        content_hash="h" * 64,
        uploaded_at=datetime.now(timezone.utc),
        needs_review=False,
    )
    defaults.update(overrides)
    return Document(**defaults)


# ───── list_workspace_documents ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_returns_all_when_no_filter():
    repo = FakeDocumentRepository()
    await repo.add(_doc(original_name="a.pdf"))
    await repo.add(_doc(original_name="b.pdf"))

    resp = await list_workspace_documents("ws-1", repo=repo)
    assert resp.total == 2


@pytest.mark.asyncio
async def test_list_filters_by_status_csv():
    repo = FakeDocumentRepository()
    await repo.add(_doc(status=DocumentStatus.ready))
    await repo.add(_doc(status=DocumentStatus.processed))
    await repo.add(_doc(status=DocumentStatus.error))

    resp = await list_workspace_documents(
        "ws-1", repo=repo, status_filter="ready,processed"
    )
    assert resp.total == 2


@pytest.mark.asyncio
async def test_list_rejects_invalid_status():
    repo = FakeDocumentRepository()

    with pytest.raises(ValidationError) as exc:
        await list_workspace_documents("ws-1", repo=repo, status_filter="banana")
    assert exc.value.code == "invalid_status"


@pytest.mark.asyncio
async def test_list_rejects_invalid_doc_type():
    repo = FakeDocumentRepository()

    with pytest.raises(ValidationError) as exc:
        await list_workspace_documents("ws-1", repo=repo, doc_type_filter="xyz")
    assert exc.value.code == "invalid_doc_type"


@pytest.mark.asyncio
async def test_list_filters_by_doc_type():
    repo = FakeDocumentRepository()
    await repo.add(_doc(doc_type=DocumentType.bank_statement))
    await repo.add(_doc(doc_type=DocumentType.credit_card_bill))

    resp = await list_workspace_documents(
        "ws-1", repo=repo, doc_type_filter="credit_card_bill"
    )
    assert resp.total == 1


# ───── get_document ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_document_raises_not_found():
    repo = FakeDocumentRepository()

    with pytest.raises(NotFoundError) as exc:
        await get_document("ws-1", "ghost", repo=repo)
    assert exc.value.code == "document_not_found"


@pytest.mark.asyncio
async def test_get_document_tenancy():
    repo = FakeDocumentRepository()
    d = await repo.add(_doc(workspace_id="ws-A"))

    with pytest.raises(NotFoundError):
        await get_document("ws-B", d.id, repo=repo)


# ───── update_document_classification ───────────────────────────────────


@pytest.mark.asyncio
async def test_update_rejects_empty_body():
    repo = FakeDocumentRepository()
    d = await repo.add(_doc())

    with pytest.raises(ValidationError) as exc:
        await update_document_classification(
            DocumentUpdateCommand(),
            workspace_id="ws-1",
            document_id=d.id,
            updated_by="user-1",
            repo=repo,
        )
    assert exc.value.code == "empty_update"


@pytest.mark.asyncio
async def test_update_records_manual_override_and_clears_review():
    repo = FakeDocumentRepository()
    d = await repo.add(_doc(needs_review=True, classification_confidence=0.4))

    resp = await update_document_classification(
        DocumentUpdateCommand(bank_code="c6bank"),
        workspace_id="ws-1",
        document_id=d.id,
        updated_by="user-1",
        repo=repo,
    )
    assert resp.bank_code == "c6bank"
    assert resp.needs_review is False
    assert resp.classification_confidence == 1.0
    meta = d.classification_meta or {}
    assert meta["manual_override"]["by"] == "user-1"
    assert meta["manual_override"]["fields"] == ["bank_code"]


@pytest.mark.asyncio
async def test_update_doc_type_invalidates_e2_extract():
    repo = FakeDocumentRepository()
    d = await repo.add(
        _doc(
            status=DocumentStatus.processed,
            pipeline_last_run_at=datetime.now(timezone.utc),
            pipeline_e2_extract_ok=True,
        )
    )

    await update_document_classification(
        DocumentUpdateCommand(doc_type=DocumentType.credit_card_bill),
        workspace_id="ws-1",
        document_id=d.id,
        updated_by="user-1",
        repo=repo,
    )
    assert d.pipeline_last_run_at is None
    assert d.pipeline_e2_extract_ok is None
    assert d.status == DocumentStatus.ready


@pytest.mark.asyncio
async def test_update_period_only_preserves_extraction_flags():
    repo = FakeDocumentRepository()
    now = datetime.now(timezone.utc)
    d = await repo.add(
        _doc(
            status=DocumentStatus.processed,
            pipeline_last_run_at=now,
            pipeline_e2_extract_ok=True,
        )
    )

    await update_document_classification(
        DocumentUpdateCommand(period="2026-05"),
        workspace_id="ws-1",
        document_id=d.id,
        updated_by="user-1",
        repo=repo,
    )
    # period alone doesn't invalidate extraction
    assert d.pipeline_last_run_at == now
    assert d.pipeline_e2_extract_ok is True
    assert d.status == DocumentStatus.processed


@pytest.mark.asyncio
async def test_update_missing_raises_not_found():
    repo = FakeDocumentRepository()

    with pytest.raises(NotFoundError):
        await update_document_classification(
            DocumentUpdateCommand(bank_code="x"),
            workspace_id="ws-1",
            document_id="ghost",
            updated_by="u",
            repo=repo,
        )


# ───── delete_document ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_returns_entity_and_removes():
    repo = FakeDocumentRepository()
    d = await repo.add(_doc())

    returned = await delete_document("ws-1", d.id, repo=repo)
    assert returned.id == d.id
    assert await repo.get_by_id("ws-1", d.id) is None


@pytest.mark.asyncio
async def test_delete_missing_raises_not_found():
    repo = FakeDocumentRepository()

    with pytest.raises(NotFoundError):
        await delete_document("ws-1", "ghost", repo=repo)


# ───── list_duplicate_candidates ───────────────────────────────────────


@pytest.mark.asyncio
async def test_list_duplicates_returns_only_flagged():
    repo = FakeDocumentRepository()
    original = await repo.add(_doc(content_hash="a" * 64))
    await repo.add(
        _doc(
            content_hash="b" * 64,
            possible_duplicate_of_id=original.id,
            needs_review=True,
        )
    )
    await repo.add(_doc(content_hash="c" * 64))  # not flagged

    resp = await list_duplicate_candidates("ws-1", repo=repo)
    assert resp.total == 1
    assert resp.documents[0].possible_duplicate_of_id == original.id


@pytest.mark.asyncio
async def test_list_duplicates_skips_errored():
    repo = FakeDocumentRepository()
    await repo.add(
        _doc(
            status=DocumentStatus.error,
            possible_duplicate_of_id="x",
        )
    )

    resp = await list_duplicate_candidates("ws-1", repo=repo)
    assert resp.total == 0


# ───── reclassify_document ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reclassify_persists_new_fields(tmp_path: Path):
    repo = FakeDocumentRepository()
    d = await repo.add(
        _doc(
            doc_type=DocumentType.other,
            bank_code=None,
            period=None,
            classification_confidence=0.3,
            needs_review=True,
        )
    )
    file_path = tmp_path / "extrato.pdf"
    file_path.write_bytes(b"%PDF-1.4 placeholder")

    classifier = FakeClassificationService(
        result={
            "doc_type": DocumentType.bank_statement,
            "bank_code": "itau",
            "period": "2026-04",
            "confidence": 0.95,
            "needs_review": False,
            "classification_meta": {"source": "content_regex"},
        }
    )

    resp = await reclassify_document(
        "ws-1",
        d.id,
        abs_path=file_path,
        classification_base=tmp_path,
        repo=repo,
        classifier=classifier,
    )
    assert resp.doc_type == DocumentType.bank_statement.value
    assert resp.bank_code == "itau"
    assert resp.period == "2026-04"
    assert resp.needs_review is False
    assert classifier.calls == [(file_path, tmp_path)]
    meta = d.classification_meta or {}
    assert "reclassified_at" in meta


@pytest.mark.asyncio
async def test_reclassify_rejects_missing_file(tmp_path: Path):
    repo = FakeDocumentRepository()
    d = await repo.add(_doc())
    missing = tmp_path / "ghost.pdf"

    classifier = FakeClassificationService(result={"doc_type": DocumentType.other})

    with pytest.raises(ValidationError) as exc:
        await reclassify_document(
            "ws-1",
            d.id,
            abs_path=missing,
            classification_base=tmp_path,
            repo=repo,
            classifier=classifier,
        )
    assert exc.value.code == "stored_file_missing"
    assert classifier.calls == []


@pytest.mark.asyncio
async def test_reclassify_missing_doc_raises_not_found(tmp_path: Path):
    repo = FakeDocumentRepository()
    f = tmp_path / "file.pdf"
    f.write_bytes(b"ok")
    classifier = FakeClassificationService(result={"doc_type": DocumentType.other})

    with pytest.raises(NotFoundError):
        await reclassify_document(
            "ws-1",
            "ghost",
            abs_path=f,
            classification_base=tmp_path,
            repo=repo,
            classifier=classifier,
        )


# ───── Workspace isolation ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_workspace_isolation_on_list():
    repo = FakeDocumentRepository()
    await repo.add(_doc(workspace_id="ws-A"))
    await repo.add(_doc(workspace_id="ws-B"))

    a = await list_workspace_documents("ws-A", repo=repo)
    b = await list_workspace_documents("ws-B", repo=repo)
    assert a.total == 1 and b.total == 1
