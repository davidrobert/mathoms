"""Documents API — upload, list, delete, retry-unlock (tenant-scoped, ADR-072)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.models.password_vault import PasswordVault
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentUploadResponse,
)
from backend.app.services.audit import AuditAction, audit_log
from backend.app.services.config_materializer import ensure_tenant_pipeline_config
from backend.app.services.document_duplicates import rebuild_fuzzy_duplicate_pointers
from backend.app.services.storage import StorageService, detect_actual_mime
from backend.app.services.vault import get_vault
from backend.app.services.document_processor import process_uploaded_document
from backend.app.services.document_pipeline_sync import _find_e2_extract

router = APIRouter(
    prefix="/workspaces/{workspace_id}/documents",
    tags=["documents"],
)
_storage = StorageService()


async def _get_vault_passwords(ws_id: str, db: AsyncSession) -> list[str]:
    """Decrypt all vault passwords for a workspace."""
    result = await db.execute(
        select(PasswordVault).where(PasswordVault.workspace_id == ws_id)
    )
    entries = result.scalars().all()
    if not entries:
        return []
    vault_svc = get_vault()
    passwords = []
    for entry in entries:
        pw = vault_svc.decrypt(entry.encrypted_password)
        if pw:
            passwords.append(pw)
    return passwords


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_role)],
)
async def upload_documents(
    request: Request,
    files: list[UploadFile] = File(...),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more documents. Each is saved, validated, unlocked (if PDF), and classified."""
    if len(files) > settings.MAX_UPLOAD_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo de {settings.MAX_UPLOAD_BATCH_SIZE} arquivos por upload",
        )

    within_quota, current_bytes = _storage.check_workspace_quota(workspace.id)
    if not within_quota:
        raise HTTPException(
            status_code=413,
            detail=f"Quota de storage excedida ({settings.MAX_STORAGE_PER_WORKSPACE_MB}MB)",
        )

    passwords = await _get_vault_passwords(workspace.id, db)
    config_dir = settings.PIPELINE_ROOT / "config"
    tenant_root = _storage.ensure_tenant_dirs(workspace.id)
    ensure_tenant_pipeline_config(workspace.id, tenant_root)
    created_docs = []

    skipped_duplicates: list[str] = []

    for upload_file in files:
        filename = upload_file.filename or "unknown"
        content = await upload_file.read()

        # Detect MIME from magic bytes — more reliable than the HTTP header,
        # which reflects the file extension chosen by the browser and can be
        # wrong (e.g. a PDF exported with a .csv name).
        actual_mime = detect_actual_mime(content) or upload_file.content_type

        ok, err_msg = _storage.validate_file(filename, len(content), content=content)
        if not ok:
            doc = Document(
                workspace_id=workspace.id,
                original_name=filename,
                status=DocumentStatus.error,
                file_size_bytes=len(content),
                content_type=actual_mime,
                error_message=err_msg,
            )
            db.add(doc)
            created_docs.append(doc)
            continue

        if len(content) == 0:
            doc = Document(
                workspace_id=workspace.id,
                original_name=filename,
                status=DocumentStatus.error,
                file_size_bytes=0,
                content_type=actual_mime,
                error_message="Arquivo vazio",
            )
            db.add(doc)
            created_docs.append(doc)
            continue

        content_hash = hashlib.sha256(content).hexdigest()

        # Atomic dedup: rely on partial unique index
        # `ux_documents_workspace_content_hash` (migration f1a2b3c4d5e6).
        # Racing uploads of the same file hash against the index; at most
        # one INSERT wins, others raise IntegrityError and are treated as
        # duplicates. The file is only persisted to disk if the INSERT wins.
        savepoint = await db.begin_nested()
        try:
            stored_path = _storage.save_to_inbox(workspace.id, filename, content)
            doc = Document(
                workspace_id=workspace.id,
                original_name=filename,
                stored_path=str(stored_path),
                file_size_bytes=len(content),
                content_type=actual_mime,
                content_hash=content_hash,
                status=DocumentStatus.classifying,
            )
            db.add(doc)
            await db.flush()
        except IntegrityError:
            await savepoint.rollback()
            # Best-effort cleanup of orphaned file on disk
            try:
                if 'stored_path' in locals() and stored_path and Path(stored_path).exists():
                    Path(stored_path).unlink(missing_ok=True)
            except OSError:
                pass
            skipped_duplicates.append(filename)
            continue

        try:
            result = process_uploaded_document(
                stored_path,
                passwords,
                config_dir,
                tenant_root=tenant_root,
                workspace_id=workspace.id,
                content_hash=content_hash,
            )
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

            # P1.4 — if the LLM fallback failed for a permanent reason
            # (auth, bad request, etc), force `needs_review=True` so the UI
            # surfaces the issue to the user even if content-regex produced
            # a weakly-confident classification. Transient errors don't
            # force review because retry-unlock will naturally retry.
            meta = result.get("classification_meta") or {}
            if (meta.get("llm_error_kind") == "permanent"
                    and doc.status != DocumentStatus.error):
                doc.needs_review = True

            # Fuzzy dedupe: if another doc in this workspace has the same
            # (doc_type, bank_code, period) but a different content_hash, flag
            # this one as a possible duplicate. We don't block — user decides.
            if (
                doc.doc_type
                and doc.doc_type != DocumentType.other
                and doc.bank_code
                and doc.period
            ):
                fuzzy = await db.execute(
                    select(Document.id)
                    .where(
                        Document.workspace_id == workspace.id,
                        Document.doc_type == doc.doc_type,
                        Document.bank_code == doc.bank_code,
                        Document.period == doc.period,
                        Document.id != doc.id,
                    )
                    .limit(1)
                )
                existing_id = fuzzy.scalar_one_or_none()
                if existing_id:
                    doc.possible_duplicate_of_id = existing_id
                    doc.needs_review = True
        except Exception as exc:
            doc.status = DocumentStatus.error
            doc.error_message = f"Erro no processamento: {str(exc)[:500]}"

        created_docs.append(doc)

        # Audit: só registramos uploads que chegaram a ter row criado com
        # stored_path (ignoramos validação falha puramente, para não poluir
        # o log com spam de file-type-errado).
        if doc.stored_path:
            await audit_log(
                db,
                action=AuditAction.document_upload,
                resource_type="document",
                resource_id=doc.id,
                workspace_id=workspace.id,
                actor_user_id=current_user.id,
                request=request,
                details={
                    "filename": filename,
                    "size_bytes": len(content),
                    "content_hash": content_hash,
                    "status": doc.status.value if hasattr(doc.status, "value") else doc.status,
                },
            )

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
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """List documents in the workspace, optionally filtered by status or doc_type."""
    query = select(Document).where(Document.workspace_id == workspace.id)

    if status_filter:
        # Suporta um valor ou lista separada por vírgula: ``status=ready,processed``.
        parts = [p.strip() for p in status_filter.split(",") if p.strip()]
        allowed = {m.value for m in DocumentStatus}
        for p in parts:
            if p not in allowed:
                raise HTTPException(status_code=400, detail=f"Status inválido: {p}")
        statuses = [DocumentStatus(p) for p in parts]
        if len(statuses) == 1:
            query = query.where(Document.status == statuses[0])
        else:
            query = query.where(Document.status.in_(statuses))

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


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(require_write_role)],
)
async def update_document_classification(
    document_id: str,
    payload: DocumentUpdateRequest,
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Correção manual de classificação (tipo, instituição, período).

    Aceita envio parcial — só atualiza os campos presentes no body. Marca
    ``classification_meta.manual_override`` e zera ``needs_review`` porque
    o usuário confirmou o valor explicitamente.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.workspace_id == workspace.id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    before = {
        "doc_type": doc.doc_type.value if hasattr(doc.doc_type, "value") else doc.doc_type,
        "bank_code": doc.bank_code,
        "period": doc.period,
    }

    # Campos que afetam qual parser/LLM é usado na extração E2 — mudança invalida extrato anterior.
    EXTRACTION_AFFECTING = {"doc_type", "bank_code"}
    extraction_changed = bool(updates.keys() & EXTRACTION_AFFECTING)

    if "doc_type" in updates:
        doc.doc_type = updates["doc_type"]
    if "bank_code" in updates:
        doc.bank_code = updates["bank_code"]
    if "period" in updates:
        doc.period = updates["period"]

    meta = dict(doc.classification_meta or {})
    meta["manual_override"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "by": current_user.id,
        "fields": sorted(updates.keys()),
    }
    doc.classification_meta = meta
    doc.classification_confidence = 1.0
    doc.needs_review = False

    if extraction_changed:
        # Invalida extrato anterior e recoloca o doc na fila do pipeline incremental.
        doc.pipeline_last_run_at = None
        doc.pipeline_e2_extract_ok = None
        if doc.status == DocumentStatus.processed:
            doc.status = DocumentStatus.ready

    await audit_log(
        db,
        action=AuditAction.document_update_classification,
        resource_type="document",
        resource_id=doc.id,
        workspace_id=workspace.id,
        actor_user_id=current_user.id,
        request=request,
        details={"before": before, "after": updates},
    )

    await db.commit()
    await db.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_role)],
)
async def delete_document(
    document_id: str,
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its file from storage."""
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.workspace_id == workspace.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    audit_details = {
        "original_name": doc.original_name,
        "content_hash": doc.content_hash,
        "doc_type": doc.doc_type.value if hasattr(doc.doc_type, "value") else doc.doc_type,
    }

    abs_stored = _storage.abs_stored_file(workspace.id, doc.stored_path)
    if abs_stored and abs_stored.exists():
        abs_stored.unlink(missing_ok=True)

    await db.delete(doc)

    await audit_log(
        db,
        action=AuditAction.document_delete,
        resource_type="document",
        resource_id=document_id,
        workspace_id=workspace.id,
        actor_user_id=current_user.id,
        request=request,
        details=audit_details,
    )

    await db.commit()


@router.post(
    "/retry-unlock",
    response_model=list[DocumentResponse],
    dependencies=[Depends(require_write_role)],
)
async def retry_unlock(
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-attempt unlock on all documents with status 'needs_password' using current vault."""
    passwords = await _get_vault_passwords(workspace.id, db)
    if not passwords:
        raise HTTPException(status_code=400, detail="Nenhuma senha cadastrada no vault")

    result = await db.execute(
        select(Document).where(
            Document.workspace_id == workspace.id,
            Document.status == DocumentStatus.needs_password,
        )
    )
    docs = result.scalars().all()
    if not docs:
        raise HTTPException(status_code=404, detail="Nenhum documento pendente de senha")

    config_dir = settings.PIPELINE_ROOT / "config"
    tenant_root = _storage.ensure_tenant_dirs(workspace.id)
    updated = []

    for doc in docs:
        abs_doc = _storage.abs_stored_file(workspace.id, doc.stored_path)
        if not doc.stored_path or not abs_doc or not abs_doc.exists():
            doc.status = DocumentStatus.error
            doc.error_message = "Arquivo não encontrado no storage"
            updated.append(doc)
            continue

        try:
            proc_result = process_uploaded_document(
                abs_doc,
                passwords,
                config_dir,
                tenant_root=tenant_root,
                workspace_id=workspace.id,
                content_hash=doc.content_hash,
            )
            doc.status = proc_result["status"]
            doc.doc_type = proc_result["doc_type"]
            doc.bank_code = proc_result["bank_code"]
            doc.period = proc_result["period"]
            doc.classification_meta = proc_result["classification_meta"]
            doc.error_message = proc_result["error_message"]
            rel = proc_result.get("stored_path_relative")
            if rel:
                doc.stored_path = rel
        except Exception as exc:
            doc.status = DocumentStatus.error
            doc.error_message = f"Erro no retry: {str(exc)[:500]}"

        updated.append(doc)

    await audit_log(
        db,
        action=AuditAction.document_retry_unlock,
        resource_type="workspace",
        resource_id=workspace.id,
        workspace_id=workspace.id,
        actor_user_id=current_user.id,
        request=request,
        details={
            "total_attempted": len(updated),
            "total_ready": sum(1 for d in updated if d.status == DocumentStatus.ready),
            "total_errored": sum(1 for d in updated if d.status == DocumentStatus.error),
        },
    )

    await db.commit()
    for doc in updated:
        await db.refresh(doc)

    return [DocumentResponse.model_validate(d) for d in updated]


@router.get(
    "/{document_id}/file",
    response_class=FileResponse,
    responses={
        200: {
            "description": (
                "Arquivo original (PDF, CSV, XLSX, imagem...). "
                "``Content-Disposition`` é ``inline`` para PDFs/imagens, "
                "``attachment`` caso contrário."
            ),
            "content": {"application/octet-stream": {}},
        },
    },
)
async def get_document_file(
    document_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Serve o arquivo original de um documento para visualização ou download.

    PDFs são servidos com ``Content-Disposition: inline`` para que o navegador
    os abra diretamente. Outros formatos recebem ``attachment`` e são baixados.
    Requer autenticação Bearer (igual a todos os outros endpoints).
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    abs_path = _storage.abs_stored_file(workspace.id, doc.stored_path)
    if abs_path is None or not abs_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no storage")

    content_type = doc.content_type or "application/octet-stream"
    # PDFs e imagens renderizam inline no browser; demais formatos são baixados.
    disposition = "inline" if ("pdf" in content_type or content_type.startswith("image/")) else "attachment"
    safe_name = doc.original_name.replace('"', "'")

    return FileResponse(
        path=str(abs_path),
        media_type=content_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{safe_name}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


class ExtractJsonResponse(BaseModel):
    filename: str
    data: Any
    all_candidates: list[str]


@router.get("/{document_id}/extract-json", response_model=ExtractJsonResponse)
async def get_document_extract_json(
    document_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Retorna o JSON extraído pelo E2 para um documento processado (dev/debug)."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    e2_dir = _storage.tenant_root(workspace.id) / "processed" / "E2_extracts"
    if not e2_dir.exists():
        raise HTTPException(status_code=404, detail="Nenhum extrato E2 disponível")

    all_candidates = sorted(f.name for f in e2_dir.glob("*-2_extract.json"))
    if not all_candidates:
        raise HTTPException(status_code=404, detail="Nenhum extrato E2 encontrado")

    # Estratégia 1: correspondência exata via stored_path (mesmo algoritmo do sync)
    target = None
    if doc.stored_path:
        source_filename = Path(doc.stored_path).name
        target = _find_e2_extract(e2_dir, source_filename)

    # Estratégia 2: fallback por bank_code + doc_type + period (sem stored_path)
    if target is None:
        matches = list(e2_dir.glob("*-2_extract.json"))
        if doc.bank_code:
            bank_matches = [f for f in matches if doc.bank_code.lower() in f.name.lower()]
            if bank_matches:
                matches = bank_matches
        # Filtra por tipo de documento antes do período para evitar confusão extrato×fatura
        _DOC_TYPE_KEYWORDS = {
            DocumentType.credit_card_bill: ["fatura"],
            DocumentType.bank_statement: ["extrato"],
        }
        if doc.doc_type in _DOC_TYPE_KEYWORDS:
            kws = _DOC_TYPE_KEYWORDS[doc.doc_type]
            type_matches = [f for f in matches if any(kw in f.name.lower() for kw in kws)]
            if type_matches:
                matches = type_matches
        if doc.period:
            period_prefix = doc.period.split("_")[0]
            period_matches = [f for f in matches if period_prefix in f.name]
            if period_matches:
                matches = period_matches
        target = sorted(matches)[0] if matches else None

    if target is None:
        raise HTTPException(status_code=404, detail="Extrato E2 não encontrado para este documento")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao ler extrato: {exc}") from exc

    return ExtractJsonResponse(filename=target.name, data=data, all_candidates=all_candidates)


class ReclassifyResponse(BaseModel):
    total: int
    updated: int
    skipped: int
    errors: int


@router.post(
    "/reclassify",
    response_model=ReclassifyResponse,
    dependencies=[Depends(require_write_role)],
)
async def reclassify_documents(
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip_manual_overrides: bool = True,
):
    """Re-run content-first classifier on all (or non-manually-overridden) documents.

    Useful when classifier rules are updated or when documents were uploaded with
    wrong extensions and got misclassified. Documents with ``manual_override`` in
    ``classification_meta`` are skipped by default (pass ``skip_manual_overrides=false``
    to force reclassification of those too).

    Does NOT reprocess JSON members/baseline files (those are deterministic and
    classified by structure, not content regex).
    """
    import asyncio
    from functools import partial
    from backend.app.services.classification_telemetry import emit_classification_outcome
    from backend.app.services.document_classification import (
        classify_document,
        classification_can_route_to_data,
    )
    from backend.app.services.document_processor import (
        _detect_json_type,
        resolve_classification_base,
    )
    from backend.app.services.canonical_routing import rename_to_canonical

    tenant_root = _storage.ensure_tenant_dirs(workspace.id)
    ensure_tenant_pipeline_config(workspace.id, tenant_root)
    classification_base = resolve_classification_base(settings.PIPELINE_ROOT / "config", tenant_root)

    result_all = await db.execute(
        select(Document).where(Document.workspace_id == workspace.id)
    )
    docs = result_all.scalars().all()

    total = len(docs)
    n_updated = 0
    n_skipped = 0
    n_errors = 0

    loop = asyncio.get_event_loop()

    for doc in docs:
        # Skip docs with manual overrides (unless caller opts in)
        if skip_manual_overrides:
            meta = doc.classification_meta or {}
            if isinstance(meta, dict) and "manual_override" in meta:
                n_skipped += 1
                continue

        if not doc.stored_path:
            n_skipped += 1
            continue

        abs_path = _storage.abs_stored_file(doc.workspace_id, doc.stored_path)
        if abs_path is None or not abs_path.exists():
            n_skipped += 1
            continue

        try:
            prior_type = doc.doc_type
            # JSON members/baseline: classify by structure (sync, fast)
            if abs_path.suffix.lower() == ".json":
                json_type = _detect_json_type(abs_path)
                if json_type:
                    doc.doc_type = json_type
                    doc.classification_confidence = 1.0
                    doc.needs_review = False
                    doc.classification_meta = {"source": "json_structure", "reclassified": True}
                    emit_classification_outcome(
                        context="reclassify",
                        classification={
                            "doc_type": json_type,
                            "confidence": 1.0,
                            "needs_review": False,
                            "classification_meta": doc.classification_meta,
                        },
                        workspace_id=workspace.id,
                        prior_doc_type=prior_type,
                        outcome="json_structure",
                    )
                    n_updated += 1
                else:
                    n_skipped += 1
                continue

            # All other files: content regex → LLM fallback (blocking I/O in threadpool).
            # Same classifier + routing gate as upload and E0-route (pipeline).
            clf = await loop.run_in_executor(
                None, partial(classify_document, abs_path, classification_base)
            )
            emit_classification_outcome(
                context="reclassify",
                classification=clf,
                workspace_id=workspace.id,
                prior_doc_type=prior_type,
                outcome="classified",
            )
            doc.doc_type = clf["doc_type"]
            doc.bank_code = clf["bank_code"]
            doc.period = clf["period"]
            doc.classification_confidence = clf["confidence"]
            doc.needs_review = clf["needs_review"]
            meta = dict(clf.get("classification_meta") or {})
            meta["reclassified_at"] = datetime.now(timezone.utc).isoformat()
            doc.classification_meta = meta

            # Rename/move only when confident enough (same rule as upload / E0-route).
            if classification_can_route_to_data(clf):
                rename_result = await loop.run_in_executor(
                    None,
                    partial(
                        rename_to_canonical,
                        abs_path,
                        tenant_root,
                        settings.PIPELINE_ROOT,
                        dest_group=clf["dest_group"],
                        e0_doc_type=clf["e0_doc_type"],
                        institution=clf.get("bank_code"),
                        period=clf.get("period"),
                        classification_meta=meta,
                        content_hash=doc.content_hash,
                    ),
                )
                if rename_result is not None:
                    abs_new, rel_new = rename_result
                    doc.stored_path = rel_new
                    doc.original_name = abs_new.name

            n_updated += 1
        except Exception as exc:
            doc.error_message = f"Reclassify error: {str(exc)[:200]}"
            n_errors += 1

    dup_rows = await db.execute(
        select(Document).where(
            Document.workspace_id == workspace.id,
            Document.status != DocumentStatus.error,
        )
    )
    rebuild_fuzzy_duplicate_pointers(list(dup_rows.scalars().all()))

    await audit_log(
        db,
        action=AuditAction.document_update_classification,
        resource_type="workspace",
        resource_id=workspace.id,
        workspace_id=workspace.id,
        actor_user_id=current_user.id,
        request=request,
        details={"total": total, "updated": n_updated, "skipped": n_skipped, "errors": n_errors},
    )

    await db.commit()
    return ReclassifyResponse(total=total, updated=n_updated, skipped=n_skipped, errors=n_errors)
