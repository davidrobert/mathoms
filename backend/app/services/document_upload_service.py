"""Composite: upload batch de documentos (A6e.4 slice 10).

Extraído de ``api/documents.py::upload_documents`` para manter o router
thin. Escopo do composite:

1. Quota do workspace (storage).
2. Validação por-arquivo (whitelist + tamanho + MIME).
3. Dedup atômico via partial unique index (SAVEPOINT + IntegrityError).
4. Persistência no inbox + processamento síncrono (unlock + classify +
   canonical routing) via ``process_uploaded_document``.
5. Fuzzy dedupe flagging (``possible_duplicate_of_id``).
6. Retorna a lista de ``Document`` rows criados + ``skipped_duplicates``.

Não faz commit — caller (router) decide o transaction boundary. Não faz
audit_log — caller registra após o commit.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.services.config_materializer import ensure_tenant_pipeline_config
from backend.app.services.document_processor import process_uploaded_document
from backend.app.services.storage import StorageService, detect_actual_mime


@dataclass(frozen=True, slots=True)
class UploadBatchResult:
    created: list[Document]
    skipped_duplicates: list[str]


class UploadBatchError(Exception):
    """Erros de pré-condição do batch (quota, limite). Router → 400/413."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


async def upload_document_batch(
    workspace_id: str,
    files: list[UploadFile],
    *,
    db: AsyncSession,
    repo: DocumentRepository,
    storage: StorageService,
) -> UploadBatchResult:
    """Processa N uploads em sequência. Caller commita e faz ``db.refresh``."""
    _check_batch_limit(files)
    _check_workspace_quota(workspace_id, storage)

    passwords = await _load_passwords(workspace_id, db)
    config_dir = settings.PIPELINE_ROOT / "config"
    tenant_root = storage.ensure_tenant_dirs(workspace_id)
    ensure_tenant_pipeline_config(workspace_id, tenant_root)

    created: list[Document] = []
    skipped: list[str] = []
    for upload_file in files:
        await _process_single_upload(
            upload_file,
            workspace_id=workspace_id,
            passwords=passwords,
            config_dir=config_dir,
            tenant_root=tenant_root,
            db=db,
            repo=repo,
            storage=storage,
            created=created,
            skipped=skipped,
        )
    return UploadBatchResult(created=created, skipped_duplicates=skipped)


def _check_batch_limit(files: list[UploadFile]) -> None:
    if len(files) > settings.MAX_UPLOAD_BATCH_SIZE:
        raise UploadBatchError(
            f"Máximo de {settings.MAX_UPLOAD_BATCH_SIZE} arquivos por upload",
            status_code=400,
        )


def _check_workspace_quota(workspace_id: str, storage: StorageService) -> None:
    within_quota, _ = storage.check_workspace_quota(workspace_id)
    if not within_quota:
        raise UploadBatchError(
            f"Quota de storage excedida ({settings.MAX_STORAGE_PER_WORKSPACE_MB}MB)",
            status_code=413,
        )


async def _load_passwords(workspace_id: str, db: AsyncSession) -> list[str]:
    from backend.app.services.password_vault_reader import get_workspace_passwords

    return await get_workspace_passwords(workspace_id, db)


async def _process_single_upload(
    upload_file: UploadFile,
    *,
    workspace_id: str,
    passwords: list[str],
    config_dir: Path,
    tenant_root: Path,
    db: AsyncSession,
    repo: DocumentRepository,
    storage: StorageService,
    created: list[Document],
    skipped: list[str],
) -> None:
    filename = upload_file.filename or "unknown"
    content = await upload_file.read()
    actual_mime = detect_actual_mime(content) or upload_file.content_type
    content_hash = hashlib.sha256(content).hexdigest()

    if await _record_validation_failure(
        filename,
        content,
        actual_mime,
        content_hash=content_hash,
        workspace_id=workspace_id,
        db=db,
        storage=storage,
        repo=repo,
        created=created,
        skipped=skipped,
    ):
        return

    doc = await _insert_with_savepoint(
        filename=filename,
        content=content,
        actual_mime=actual_mime,
        content_hash=content_hash,
        workspace_id=workspace_id,
        db=db,
        repo=repo,
        storage=storage,
        skipped=skipped,
    )
    if doc is None:
        return

    _apply_processing_result(
        doc,
        stored_path=doc.stored_path,
        passwords=passwords,
        config_dir=config_dir,
        tenant_root=tenant_root,
        workspace_id=workspace_id,
        content_hash=content_hash,
    )
    await _apply_fuzzy_dedupe(doc, workspace_id=workspace_id, repo=repo)
    created.append(doc)


async def _record_validation_failure(
    filename: str,
    content: bytes,
    actual_mime: str | None,
    *,
    content_hash: str,
    workspace_id: str,
    db: AsyncSession,
    storage: StorageService,
    repo: DocumentRepository,
    created: list[Document],
    skipped: list[str],
) -> bool:
    """Persiste documento ``status=error`` quando validação falha ou conteúdo vazio.

    O ``content_hash`` é gravado mesmo em registros de erro — caso contrário
    o partial unique index ``ux_documents_workspace_content_hash``
    (``WHERE content_hash IS NOT NULL``) não bloqueia re-upload das mesmas
    bytes. INSERT vai num savepoint para que colisão de hash com doc
    pré-existente seja capturada como skipped em vez de propagar
    ``IntegrityError`` no commit do batch.
    """
    ok, err_msg = storage.validate_file(filename, len(content), content=content)
    if ok and len(content) > 0:
        return False
    if len(content) == 0:
        err_msg = "Arquivo vazio"

    savepoint = await db.begin_nested()
    try:
        doc = Document(
            workspace_id=workspace_id,
            original_name=filename,
            status=DocumentStatus.error,
            file_size_bytes=len(content),
            content_type=actual_mime,
            content_hash=content_hash,
            error_message=err_msg,
        )
        await repo.add(doc)
        created.append(doc)
    except IntegrityError:
        await savepoint.rollback()
        skipped.append(filename)
    return True


async def _insert_with_savepoint(
    *,
    filename: str,
    content: bytes,
    actual_mime: str | None,
    content_hash: str,
    workspace_id: str,
    db: AsyncSession,
    repo: DocumentRepository,
    storage: StorageService,
    skipped: list[str],
) -> Document | None:
    """Atomic dedup via partial unique index (ux_documents_workspace_content_hash).

    Racing uploads of the same hash lose on INSERT; orphan file cleaned up.
    """
    savepoint = await db.begin_nested()
    stored_path = None
    try:
        stored_path = storage.save_to_inbox(workspace_id, filename, content)
        doc = Document(
            workspace_id=workspace_id,
            original_name=filename,
            stored_path=str(stored_path),
            file_size_bytes=len(content),
            content_type=actual_mime,
            content_hash=content_hash,
            status=DocumentStatus.classifying,
        )
        await repo.add(doc)
        return doc
    except IntegrityError:
        await savepoint.rollback()
        try:
            if stored_path and Path(stored_path).exists():
                Path(stored_path).unlink(missing_ok=True)
        except OSError:
            pass
        skipped.append(filename)
        return None


def _apply_processing_result(
    doc: Document,
    *,
    stored_path: str | None,
    passwords: list[str],
    config_dir: Path,
    tenant_root: Path,
    workspace_id: str,
    content_hash: str,
) -> None:
    try:
        result = process_uploaded_document(
            Path(stored_path),
            passwords,
            config_dir,
            tenant_root=tenant_root,
            workspace_id=workspace_id,
            content_hash=content_hash,
        )
    except Exception as exc:
        doc.status = DocumentStatus.error
        doc.error_message = f"Erro no processamento: {str(exc)[:500]}"
        return

    doc.status = result["status"]
    doc.doc_type = result["doc_type"]
    doc.bank_code = result["bank_code"]
    doc.period = result["period"]
    doc.classification_meta = result["classification_meta"]
    doc.classification_confidence = result.get("confidence")
    doc.needs_review = bool(result.get("needs_review"))
    doc.error_message = result["error_message"]
    rel = result.get("stored_path_relative")
    if rel:
        doc.stored_path = rel

    meta = result.get("classification_meta") or {}
    if meta.get("llm_error_kind") == "permanent" and doc.status != DocumentStatus.error:
        # P1.4: LLM permanent error força needs_review mesmo com regex fraco.
        doc.needs_review = True


async def _apply_fuzzy_dedupe(
    doc: Document,
    *,
    workspace_id: str,
    repo: DocumentRepository,
) -> None:
    """Flags possível duplicata quando (doc_type, bank_code, period) colide."""
    if not doc.doc_type or doc.doc_type == DocumentType.other:
        return
    if not doc.bank_code or not doc.period:
        return
    existing_id = await repo.find_fuzzy_duplicate_id(
        workspace_id,
        doc_type=doc.doc_type,
        bank_code=doc.bank_code,
        period=doc.period,
        exclude_id=doc.id,
    )
    if existing_id:
        doc.possible_duplicate_of_id = existing_id
        doc.needs_review = True
