"""Tests for Phase 2A models — Document, PasswordVault, PipelineRun, PipelineStageLog."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Document, DocumentStatus, DocumentType,
    PasswordVault,
    PipelineRun, PipelineRunStatus,
    PipelineStageLog, PipelineStageStatus,
    User, Workspace,
)
from backend.app.core.security import hash_password


async def _make_workspace(db: AsyncSession) -> tuple[str, str]:
    """Create a user + workspace, return (user_id, workspace_id)."""
    user = User(email="model@test.com", hashed_password=hash_password("p"), full_name="M")
    db.add(user)
    await db.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    db.add(ws)
    await db.flush()
    return user.id, ws.id


@pytest.mark.asyncio
async def test_document_creation(db: AsyncSession):
    _, ws_id = await _make_workspace(db)
    doc = Document(
        workspace_id=ws_id,
        original_name="extrato_itau.pdf",
        status=DocumentStatus.uploaded,
        doc_type=DocumentType.bank_statement,
        file_size_bytes=1024,
    )
    db.add(doc)
    await db.flush()

    result = await db.execute(select(Document).where(Document.workspace_id == ws_id))
    saved = result.scalar_one()
    assert saved.original_name == "extrato_itau.pdf"
    assert saved.status == DocumentStatus.uploaded
    assert saved.doc_type == DocumentType.bank_statement


@pytest.mark.asyncio
async def test_document_status_transitions(db: AsyncSession):
    _, ws_id = await _make_workspace(db)
    doc = Document(workspace_id=ws_id, original_name="test.pdf", status=DocumentStatus.uploaded)
    db.add(doc)
    await db.flush()

    for s in [DocumentStatus.unlocking, DocumentStatus.classifying, DocumentStatus.ready]:
        doc.status = s
        await db.flush()
        assert doc.status == s

    doc.status = DocumentStatus.processed
    await db.flush()
    assert doc.status == DocumentStatus.processed


@pytest.mark.asyncio
async def test_password_vault_creation(db: AsyncSession):
    _, ws_id = await _make_workspace(db)
    entry = PasswordVault(workspace_id=ws_id, label="Itaú PDF", encrypted_password="enc")
    db.add(entry)
    await db.flush()

    result = await db.execute(select(PasswordVault).where(PasswordVault.workspace_id == ws_id))
    saved = result.scalar_one()
    assert saved.label == "Itaú PDF"


@pytest.mark.asyncio
async def test_pipeline_run_with_stage_logs(db: AsyncSession):
    _, ws_id = await _make_workspace(db)
    run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running)
    db.add(run)
    await db.flush()

    log1 = PipelineStageLog(
        pipeline_run_id=run.id, stage="E2", status=PipelineStageStatus.completed, duration_ms=1500
    )
    log2 = PipelineStageLog(
        pipeline_run_id=run.id, stage="E3", status=PipelineStageStatus.running
    )
    db.add_all([log1, log2])
    await db.flush()

    result = await db.execute(select(PipelineRun).where(PipelineRun.id == run.id))
    assert result.scalar_one().status == PipelineRunStatus.running

    logs = await db.execute(
        select(PipelineStageLog).where(PipelineStageLog.pipeline_run_id == run.id)
    )
    assert len(logs.scalars().all()) == 2


@pytest.mark.asyncio
async def test_document_type_enum_values():
    assert DocumentType.bank_statement.value == "bank_statement"
    assert DocumentType.credit_card_bill.value == "credit_card_bill"
    assert DocumentType.e1_members_json.value == "e1_members_json"
    assert DocumentType.e1_5_baseline_json.value == "e1_5_baseline_json"


@pytest.mark.asyncio
async def test_pipeline_run_status_enum_values():
    assert PipelineRunStatus.pending.value == "pending"
    assert PipelineRunStatus.partial_failure.value == "partial_failure"
    assert PipelineStageStatus.skipped.value == "skipped"
