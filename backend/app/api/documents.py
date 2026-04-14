"""Documents API — upload, list, delete, retry-unlock."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.models.password_vault import PasswordVault
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.document import DocumentListResponse, DocumentResponse, DocumentUploadResponse
from backend.app.services.storage import StorageService
from backend.app.services.vault import VaultService
from backend.app.services.document_processor import process_uploaded_document

router = APIRouter(prefix="/documents", tags=["documents"])
_storage = StorageService()


async def _get_workspace(user: User, db: AsyncSession) -> Workspace:
    result = await db.execute(select(Workspace).where(Workspace.owner_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    return ws


async def _get_vault_passwords(ws_id: str, db: AsyncSession) -> list[str]:
    """Decrypt all vault passwords for a workspace."""
    result = await db.execute(
        select(PasswordVault).where(PasswordVault.workspace_id == ws_id)
    )
    entries = result.scalars().all()
    if not entries:
        return []
    vault_svc = VaultService()
    passwords = []
    for entry in entries:
        pw = vault_svc.decrypt(entry.encrypted_password)
        if pw:
            passwords.append(pw)
    return passwords


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more documents. Each is saved, validated, unlocked (if PDF), and classified."""
    ws = await _get_workspace(user, db)

    if len(files) > settings.MAX_UPLOAD_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo de {settings.MAX_UPLOAD_BATCH_SIZE} arquivos por upload",
        )

    within_quota, current_bytes = _storage.check_workspace_quota(ws.id)
    if not within_quota:
        raise HTTPException(
            status_code=413,
            detail=f"Quota de storage excedida ({settings.MAX_STORAGE_PER_WORKSPACE_MB}MB)",
        )

    passwords = await _get_vault_passwords(ws.id, db)
    config_dir = settings.PIPELINE_ROOT / "config"
    created_docs = []

    skipped_duplicates: list[str] = []

    for upload_file in files:
        filename = upload_file.filename or "unknown"
        content = await upload_file.read()

        ok, err_msg = _storage.validate_file(filename, len(content))
        if not ok:
            doc = Document(
                workspace_id=ws.id,
                original_name=filename,
                status=DocumentStatus.error,
                file_size_bytes=len(content),
                content_type=upload_file.content_type,
                error_message=err_msg,
            )
            db.add(doc)
            created_docs.append(doc)
            continue

        if len(content) == 0:
            doc = Document(
                workspace_id=ws.id,
                original_name=filename,
                status=DocumentStatus.error,
                file_size_bytes=0,
                content_type=upload_file.content_type,
                error_message="Arquivo vazio",
            )
            db.add(doc)
            created_docs.append(doc)
            continue

        content_hash = hashlib.sha256(content).hexdigest()

        existing = await db.execute(
            select(Document.id).where(
                Document.workspace_id == ws.id,
                Document.content_hash == content_hash,
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            skipped_duplicates.append(filename)
            continue

        stored_path = _storage.save_to_inbox(ws.id, filename, content)

        doc = Document(
            workspace_id=ws.id,
            original_name=filename,
            stored_path=str(stored_path),
            file_size_bytes=len(content),
            content_type=upload_file.content_type,
            content_hash=content_hash,
            status=DocumentStatus.classifying,
        )
        db.add(doc)
        await db.flush()

        try:
            result = process_uploaded_document(stored_path, passwords, config_dir)
            doc.status = result["status"]
            doc.doc_type = result["doc_type"]
            doc.bank_code = result["bank_code"]
            doc.period = result["period"]
            doc.classification_meta = result["classification_meta"]
            doc.error_message = result["error_message"]
        except Exception as exc:
            doc.status = DocumentStatus.error
            doc.error_message = f"Erro no processamento: {str(exc)[:500]}"

        created_docs.append(doc)

    await db.commit()
    for doc in created_docs:
        await db.refresh(doc)

    return DocumentUploadResponse(
        documents=[DocumentResponse.model_validate(d) for d in created_docs],
        skipped_duplicates=skipped_duplicates,
        total_uploaded=len(created_docs),
        total_skipped=len(skipped_duplicates),
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    status_filter: Optional[str] = Query(None, alias="status"),
    doc_type_filter: Optional[str] = Query(None, alias="doc_type"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents in the workspace, optionally filtered by status or doc_type."""
    ws = await _get_workspace(user, db)
    query = select(Document).where(Document.workspace_id == ws.id)

    if status_filter:
        try:
            DocumentStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status_filter}")
        query = query.where(Document.status == status_filter)

    if doc_type_filter:
        try:
            DocumentType(doc_type_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Tipo inválido: {doc_type_filter}")
        query = query.where(Document.doc_type == doc_type_filter)

    query = query.order_by(Document.uploaded_at.desc())
    result = await db.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its file from storage."""
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.workspace_id == ws.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if doc.stored_path:
        stored = Path(doc.stored_path)
        if stored.exists():
            stored.unlink(missing_ok=True)

    await db.delete(doc)
    await db.commit()


@router.post("/retry-unlock", response_model=list[DocumentResponse])
async def retry_unlock(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-attempt unlock on all documents with status 'needs_password' using current vault."""
    ws = await _get_workspace(user, db)
    passwords = await _get_vault_passwords(ws.id, db)
    if not passwords:
        raise HTTPException(status_code=400, detail="Nenhuma senha cadastrada no vault")

    result = await db.execute(
        select(Document).where(
            Document.workspace_id == ws.id,
            Document.status == DocumentStatus.needs_password,
        )
    )
    docs = result.scalars().all()
    if not docs:
        raise HTTPException(status_code=404, detail="Nenhum documento pendente de senha")

    config_dir = settings.PIPELINE_ROOT / "config"
    updated = []

    for doc in docs:
        if not doc.stored_path or not Path(doc.stored_path).exists():
            doc.status = DocumentStatus.error
            doc.error_message = "Arquivo não encontrado no storage"
            updated.append(doc)
            continue

        try:
            proc_result = process_uploaded_document(
                Path(doc.stored_path), passwords, config_dir
            )
            doc.status = proc_result["status"]
            doc.doc_type = proc_result["doc_type"]
            doc.bank_code = proc_result["bank_code"]
            doc.period = proc_result["period"]
            doc.classification_meta = proc_result["classification_meta"]
            doc.error_message = proc_result["error_message"]
        except Exception as exc:
            doc.status = DocumentStatus.error
            doc.error_message = f"Erro no retry: {str(exc)[:500]}"

        updated.append(doc)

    await db.commit()
    for doc in updated:
        await db.refresh(doc)

    return [DocumentResponse.model_validate(d) for d in updated]
