"""Testes unitários do DocumentRepository (com DB real).

Usam as fixtures ``db`` / ``setup_db`` de conftest.py (SQLite in-memory).
Cobrem:

- list com filtros (statuses [=, IN, lista vazia], doc_type).
- Isolamento multi-tenant (R13) — ws_a nunca enxerga docs de ws_b.
- get_by_id / get_by_content_hash dentro do workspace.
- find_fuzzy_duplicate_id: match por triplo (doc_type, bank_code,
  period); ``exclude_id`` funciona; retorna ``None`` sem match.
- list_non_error omite docs em ``error``.
- add + flush devolve id disponível antes do commit.
- delete remove a row (sem commit no repo).
- Ordenação por ``uploaded_at`` DESC.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.models.workspace import Workspace
from backend.app.repositories.document_repository import DocumentRepository
from backend.tests.factories.builders import make_document, make_workspace


@pytest_asyncio.fixture
async def two_workspaces(db: AsyncSession) -> tuple[Workspace, Workspace]:
    """Dois workspaces persistidos — valida isolamento multi-tenant."""
    ws_a = await make_workspace(db, name="WS A")
    ws_b = await make_workspace(db, name="WS B")
    await db.commit()
    return ws_a, ws_b


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_returns_empty_for_empty_workspace(
    db: AsyncSession, two_workspaces
):
    ws_a, _ = two_workspaces
    repo = DocumentRepository(db)

    assert (await repo.list(ws_a.id)) == []


@pytest.mark.asyncio
async def test_list_is_isolated_per_workspace(
    db: AsyncSession, two_workspaces
):
    ws_a, ws_b = two_workspaces

    await make_document(db, workspace=ws_a, original_name="a1.pdf")
    await make_document(db, workspace=ws_a, original_name="a2.pdf")
    await make_document(db, workspace=ws_b, original_name="b1.pdf")
    await db.commit()

    repo = DocumentRepository(db)
    docs_a = await repo.list(ws_a.id)
    docs_b = await repo.list(ws_b.id)

    assert {d.original_name for d in docs_a} == {"a1.pdf", "a2.pdf"}
    assert {d.original_name for d in docs_b} == {"b1.pdf"}


@pytest.mark.asyncio
async def test_list_filters_by_single_status(
    db: AsyncSession, two_workspaces
):
    ws_a, _ = two_workspaces

    await make_document(db, workspace=ws_a, status="ready", original_name="r.pdf")
    await make_document(db, workspace=ws_a, status="error", original_name="e.pdf")
    await db.commit()

    repo = DocumentRepository(db)
    docs = await repo.list(ws_a.id, statuses=[DocumentStatus.ready])

    assert len(docs) == 1
    assert docs[0].original_name == "r.pdf"


@pytest.mark.asyncio
async def test_list_filters_by_status_in_clause(
    db: AsyncSession, two_workspaces
):
    ws_a, _ = two_workspaces

    await make_document(db, workspace=ws_a, status="ready", original_name="r.pdf")
    await make_document(db, workspace=ws_a, status="processed", original_name="p.pdf")
    await make_document(db, workspace=ws_a, status="error", original_name="e.pdf")
    await db.commit()

    repo = DocumentRepository(db)
    docs = await repo.list(
        ws_a.id, statuses=[DocumentStatus.ready, DocumentStatus.processed]
    )

    assert {d.original_name for d in docs} == {"r.pdf", "p.pdf"}


@pytest.mark.asyncio
async def test_list_with_empty_statuses_returns_empty(
    db: AsyncSession, two_workspaces
):
    """``statuses=[]`` é interpretado como "filtro impossível", curto-circuita."""
    ws_a, _ = two_workspaces
    await make_document(db, workspace=ws_a)
    await db.commit()

    repo = DocumentRepository(db)

    assert (await repo.list(ws_a.id, statuses=[])) == []


@pytest.mark.asyncio
async def test_list_filters_by_doc_type(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_document(db, workspace=ws_a, doc_type="bank_statement", original_name="b.pdf")
    await make_document(db, workspace=ws_a, doc_type="credit_card_bill", original_name="c.pdf")
    await db.commit()

    repo = DocumentRepository(db)
    docs = await repo.list(ws_a.id, doc_type=DocumentType.credit_card_bill)

    assert len(docs) == 1
    assert docs[0].original_name == "c.pdf"


@pytest.mark.asyncio
async def test_list_orders_by_uploaded_at_desc(
    db: AsyncSession, two_workspaces
):
    ws_a, _ = two_workspaces

    older = await make_document(db, workspace=ws_a, original_name="older.pdf")
    newer = await make_document(db, workspace=ws_a, original_name="newer.pdf")
    older.uploaded_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer.uploaded_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    await db.commit()

    repo = DocumentRepository(db)
    docs = await repo.list(ws_a.id)

    assert [d.original_name for d in docs] == ["newer.pdf", "older.pdf"]


# ---------------------------------------------------------------------------
# get_by_id / get_by_content_hash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_id_scoped_to_workspace(
    db: AsyncSession, two_workspaces
):
    ws_a, ws_b = two_workspaces

    doc = await make_document(db, workspace=ws_a)
    await db.commit()

    repo = DocumentRepository(db)

    assert (await repo.get_by_id(ws_a.id, doc.id)) is not None
    # Cross-tenant: ws_b não deve enxergar o doc de ws_a.
    assert (await repo.get_by_id(ws_b.id, doc.id)) is None
    # Id inexistente.
    assert (await repo.get_by_id(ws_a.id, "nonexistent")) is None


@pytest.mark.asyncio
async def test_get_by_content_hash_scoped_to_workspace(
    db: AsyncSession, two_workspaces
):
    ws_a, ws_b = two_workspaces

    await make_document(db, workspace=ws_a, content_hash="shared_hash_123")
    await db.commit()

    repo = DocumentRepository(db)
    assert (await repo.get_by_content_hash(ws_a.id, "shared_hash_123")) is not None
    # O mesmo hash em ws_b é tratado como distinto (partial unique index por (ws, hash)).
    assert (await repo.get_by_content_hash(ws_b.id, "shared_hash_123")) is None


# ---------------------------------------------------------------------------
# find_fuzzy_duplicate_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_fuzzy_duplicate_id_matches_triplo(
    db: AsyncSession, two_workspaces
):
    ws_a, _ = two_workspaces

    original = await make_document(
        db,
        workspace=ws_a,
        original_name="original.pdf",
        doc_type="bank_statement",
        bank_code="itau",
        period="202601",
        content_hash="hash_original",
    )
    dup_candidate = await make_document(
        db,
        workspace=ws_a,
        original_name="duplicate.pdf",
        doc_type="bank_statement",
        bank_code="itau",
        period="202601",
        content_hash="hash_different",
    )
    await db.commit()

    repo = DocumentRepository(db)
    found = await repo.find_fuzzy_duplicate_id(
        ws_a.id,
        doc_type=DocumentType.bank_statement,
        bank_code="itau",
        period="202601",
        exclude_id=dup_candidate.id,
    )
    assert found == original.id


@pytest.mark.asyncio
async def test_find_fuzzy_duplicate_id_returns_none_without_match(
    db: AsyncSession, two_workspaces
):
    ws_a, _ = two_workspaces
    await make_document(
        db, workspace=ws_a, doc_type="bank_statement", bank_code="itau", period="202601"
    )
    await db.commit()

    repo = DocumentRepository(db)
    found = await repo.find_fuzzy_duplicate_id(
        ws_a.id,
        doc_type=DocumentType.bank_statement,
        bank_code="c6bank",
        period="202601",
    )
    assert found is None


@pytest.mark.asyncio
async def test_find_fuzzy_duplicate_id_is_workspace_isolated(
    db: AsyncSession, two_workspaces
):
    ws_a, ws_b = two_workspaces
    await make_document(
        db, workspace=ws_a, doc_type="bank_statement", bank_code="itau", period="202601"
    )
    await db.commit()

    repo = DocumentRepository(db)
    found = await repo.find_fuzzy_duplicate_id(
        ws_b.id,
        doc_type=DocumentType.bank_statement,
        bank_code="itau",
        period="202601",
    )
    assert found is None


# ---------------------------------------------------------------------------
# list_non_error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_non_error_excludes_error_status(
    db: AsyncSession, two_workspaces
):
    ws_a, _ = two_workspaces

    await make_document(db, workspace=ws_a, status="ready", original_name="r.pdf")
    await make_document(db, workspace=ws_a, status="processed", original_name="p.pdf")
    await make_document(db, workspace=ws_a, status="error", original_name="e.pdf")
    await db.commit()

    repo = DocumentRepository(db)
    docs = await repo.list_non_error(ws_a.id)

    assert {d.original_name for d in docs} == {"r.pdf", "p.pdf"}


# ---------------------------------------------------------------------------
# add + delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_flushes_and_assigns_id(
    db: AsyncSession, two_workspaces
):
    ws_a, _ = two_workspaces

    doc = Document(
        workspace_id=ws_a.id,
        original_name="new.pdf",
        stored_path="some/path.pdf",
        status=DocumentStatus.classifying,
    )
    repo = DocumentRepository(db)
    returned = await repo.add(doc)

    assert returned is doc
    assert doc.id is not None
    await db.commit()


@pytest.mark.asyncio
async def test_add_with_flush_false_does_not_flush(
    db: AsyncSession, two_workspaces
):
    ws_a, _ = two_workspaces

    doc = Document(
        workspace_id=ws_a.id,
        original_name="nf.pdf",
        stored_path="nf.pdf",
        status=DocumentStatus.uploaded,
    )
    repo = DocumentRepository(db)
    await repo.add(doc, flush=False)

    # ``flush=False`` significa que o INSERT não foi emitido — o default
    # lambda do ``id`` é disparado pelo SQLAlchemy só no flush/commit.
    assert doc.id is None
    await db.commit()
    assert doc.id is not None


@pytest.mark.asyncio
async def test_delete_removes_row(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    doc = await make_document(db, workspace=ws_a)
    await db.commit()

    repo = DocumentRepository(db)
    await repo.delete(doc)
    await db.commit()

    assert (await repo.get_by_id(ws_a.id, doc.id)) is None
