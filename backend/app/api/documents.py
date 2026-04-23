"""Documents API — thin router (A6e.4 slice 10 · fase 4b · ADR-101 R15/R16).

Handlers delegam a use cases em ``backend/app/application/document/``
ou services de composite em ``backend/app/services/document_*``:

- **Pure CRUD** (use cases): ``list``, ``update_classification``, ``delete``.
- **Composites extraídos** (services): ``upload_document_batch``,
  ``retry_unlock_workspace_documents``, ``reclassify_workspace_documents``,
  ``read_document_extract_json``.
- **File serve** (FileResponse): ``get_document_file`` usa StorageService
  diretamente — thin o suficiente.

Audit emitido via ``AuditLogEvent`` + ``dispatch_sync`` (A6e.events-migration,
ADR-115). Router nivel porque composites não passam por use case fino.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.document import (
    delete_document as _uc_delete_document,
)
from backend.app.application.document import (
    list_workspace_documents as _uc_list_workspace_documents,
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.events import dispatch_sync
from backend.app.events.domain import AuditLogEvent
from backend.app.models.document import Document, DocumentStatus
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.schemas.dto.document import (
    DocumentExtractJsonResponse,
    DocumentListResponse,
    DocumentReclassifyResponse,
    DocumentResponse,
    DocumentUpdateCommand,
    DocumentUploadResponse,
    document_to_response,
)
from backend.app.services.audit import AuditAction, client_meta
from backend.app.services.document_extract_json_service import (
    DocumentExtractError,
    read_document_extract_json,
)
from backend.app.services.document_reclassify_bulk_service import (
    reclassify_workspace_documents,
)
from backend.app.services.document_retry_service import (
    RetryUnlockError,
    retry_unlock_workspace_documents,
)
from backend.app.services.document_upload_service import (
    UploadBatchError,
    upload_document_batch,
)
from backend.app.services.storage import StorageService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/documents",
    tags=["documents"],
)
_storage = StorageService()


def _get_document_repo(
    db: AsyncSession = Depends(get_db),
) -> DocumentRepository:
    """FastAPI dependency: DocumentRepository bound à sessão do request."""
    return DocumentRepository(db)


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
    repo: DocumentRepository = Depends(_get_document_repo),
) -> DocumentUploadResponse:
    """Upload N documentos. Composite (storage + classify + fuzzy dedup + savepoint).

    Audit registrado por doc com ``stored_path`` não-nulo (ignora falhas
    puras de validação para não poluir o log).
    """
    try:
        result = await upload_document_batch(
            workspace.id, files, db=db, repo=repo, storage=_storage
        )
    except UploadBatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    ip, ua = client_meta(request)
    for doc in result.created:
        if doc.stored_path:
            await dispatch_sync(
                AuditLogEvent(
                    aggregate_id=doc.id,
                    aggregate_type="document",
                    workspace_id=workspace.id,
                    action=AuditAction.document_upload.value,
                    resource_type="document",
                    resource_id=doc.id,
                    actor_user_id=current_user.id,
                    ip_address=ip,
                    user_agent=ua,
                    details={
                        "filename": doc.original_name,
                        "size_bytes": doc.file_size_bytes,
                        "content_hash": doc.content_hash,
                        "status": doc.status.value if hasattr(doc.status, "value") else doc.status,
                    },
                ),
                {"db": db},
            )

    await db.commit()
    for doc in result.created:
        await db.refresh(doc)

    return DocumentUploadResponse(
        documents=[document_to_response(d) for d in result.created],
        skipped_duplicates=result.skipped_duplicates,
        total_uploaded=len(result.created),
        total_skipped=len(result.skipped_duplicates),
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    status_filter: Optional[str] = Query(None, alias="status"),
    doc_type_filter: Optional[str] = Query(None, alias="doc_type"),
    workspace: Workspace = Depends(get_current_workspace),
    repo: DocumentRepository = Depends(_get_document_repo),
) -> DocumentListResponse:
    """List documents, filtrados por status (CSV) ou doc_type."""
    return await _uc_list_workspace_documents(
        workspace.id,
        repo=repo,
        status_filter=status_filter,
        doc_type_filter=doc_type_filter,
    )


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(require_write_role)],
)
async def update_document_classification(
    document_id: str,
    payload: DocumentUpdateCommand,
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: DocumentRepository = Depends(_get_document_repo),
) -> DocumentResponse:
    """Correção manual de classificação (tipo, instituição, período).

    Aceita envio parcial — só atualiza os campos presentes no body. Marca
    ``classification_meta.manual_override`` e zera ``needs_review``.
    """
    before = await _snapshot_classification_before(workspace.id, document_id, repo)
    response = await _apply_classification_update(
        payload, workspace.id, document_id, current_user.id, repo
    )
    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=document_id,
            aggregate_type="document",
            workspace_id=workspace.id,
            action=AuditAction.document_update_classification.value,
            resource_type="document",
            resource_id=document_id,
            actor_user_id=current_user.id,
            ip_address=ip,
            user_agent=ua,
            details={"before": before, "after": payload.model_dump(exclude_unset=True)},
        ),
        {"db": db},
    )
    await db.commit()
    return response


async def _snapshot_classification_before(
    workspace_id: str, document_id: str, repo: DocumentRepository
) -> dict:
    doc = await repo.get_by_id(workspace_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return {
        "doc_type": doc.doc_type.value if hasattr(doc.doc_type, "value") else doc.doc_type,
        "bank_code": doc.bank_code,
        "period": doc.period,
    }


async def _apply_classification_update(
    payload: DocumentUpdateCommand,
    workspace_id: str,
    document_id: str,
    actor_user_id: str,
    repo: DocumentRepository,
) -> DocumentResponse:
    """Aplica fields + manual_override meta + invalida E2 quando necessário.

    Lógica inline porque o use case ``application/document/update_document_classification``
    ainda não cobre invalidação E2 + downgrade de status (só aplica fields +
    marca manual_override). Candidato a migração quando houver segundo
    consumidor.
    """
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    doc = await repo.get_by_id(workspace_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    _apply_classification_fields(doc, updates, actor_user_id)
    _invalidate_e2_if_needed(doc, updates)
    return document_to_response(doc)


def _apply_classification_fields(doc: Document, updates: dict, actor_user_id: str) -> None:
    if "doc_type" in updates:
        doc.doc_type = updates["doc_type"]
    if "bank_code" in updates:
        doc.bank_code = updates["bank_code"]
    if "period" in updates:
        doc.period = updates["period"]
    meta = dict(doc.classification_meta or {})
    meta["manual_override"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "by": actor_user_id,
        "fields": sorted(updates.keys()),
    }
    doc.classification_meta = meta
    doc.classification_confidence = 1.0
    doc.needs_review = False


def _invalidate_e2_if_needed(doc: Document, updates: dict) -> None:
    """Se ``doc_type``/``bank_code`` mudou, extrato E2 antigo fica inválido —
    recoloca doc na fila do pipeline incremental."""
    extraction_affecting = {"doc_type", "bank_code"}
    if not (updates.keys() & extraction_affecting):
        return
    doc.pipeline_last_run_at = None
    doc.pipeline_e2_extract_ok = None
    if doc.status == DocumentStatus.processed:
        doc.status = DocumentStatus.ready


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
    repo: DocumentRepository = Depends(_get_document_repo),
) -> None:
    """Remove a row + arquivo do storage + audit entry."""
    doc = await _uc_delete_document(workspace.id, document_id, repo=repo)
    audit_details = {
        "original_name": doc.original_name,
        "content_hash": doc.content_hash,
        "doc_type": doc.doc_type.value if hasattr(doc.doc_type, "value") else doc.doc_type,
    }
    abs_stored = _storage.abs_stored_file(workspace.id, doc.stored_path)
    if abs_stored and abs_stored.exists():
        abs_stored.unlink(missing_ok=True)
    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=document_id,
            aggregate_type="document",
            workspace_id=workspace.id,
            action=AuditAction.document_delete.value,
            resource_type="document",
            resource_id=document_id,
            actor_user_id=current_user.id,
            ip_address=ip,
            user_agent=ua,
            details=audit_details,
        ),
        {"db": db},
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
    repo: DocumentRepository = Depends(_get_document_repo),
) -> list[DocumentResponse]:
    """Re-attempt unlock em todos os docs com status 'needs_password'."""
    try:
        updated, stats = await retry_unlock_workspace_documents(
            workspace.id, db=db, repo=repo, storage=_storage
        )
    except RetryUnlockError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=workspace.id,
            aggregate_type="workspace",
            workspace_id=workspace.id,
            action=AuditAction.document_retry_unlock.value,
            resource_type="workspace",
            resource_id=workspace.id,
            actor_user_id=current_user.id,
            ip_address=ip,
            user_agent=ua,
            details={
                "total_attempted": stats.total_attempted,
                "total_ready": stats.total_ready,
                "total_errored": stats.total_errored,
            },
        ),
        {"db": db},
    )
    await db.commit()
    for doc in updated:
        await db.refresh(doc)
    return [document_to_response(d) for d in updated]


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
    repo: DocumentRepository = Depends(_get_document_repo),
) -> FileResponse:
    """Serve o arquivo original para visualização ou download.

    PDFs/imagens com ``Content-Disposition: inline`` (abrem no browser);
    demais formatos como ``attachment`` (download).
    """
    doc = await repo.get_by_id(workspace.id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    abs_path = _storage.abs_stored_file(workspace.id, doc.stored_path)
    if abs_path is None or not abs_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no storage")

    content_type = doc.content_type or "application/octet-stream"
    disposition = (
        "inline" if ("pdf" in content_type or content_type.startswith("image/")) else "attachment"
    )
    safe_name = doc.original_name.replace('"', "'")
    return FileResponse(
        path=str(abs_path),
        media_type=content_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{safe_name}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/{document_id}/extract-json", response_model=DocumentExtractJsonResponse)
async def get_document_extract_json(
    document_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: DocumentRepository = Depends(_get_document_repo),
) -> DocumentExtractJsonResponse:
    """Retorna o JSON extraído pelo E2 para um documento processado (dev/debug)."""
    doc = await repo.get_by_id(workspace.id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    try:
        result = read_document_extract_json(doc, workspace_id=workspace.id, storage=_storage)
    except DocumentExtractError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return DocumentExtractJsonResponse(
        filename=result.filename, data=result.data, all_candidates=result.all_candidates
    )


@router.post(
    "/reclassify",
    response_model=DocumentReclassifyResponse,
    dependencies=[Depends(require_write_role)],
)
async def reclassify_documents(
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: DocumentRepository = Depends(_get_document_repo),
    skip_manual_overrides: bool = True,
) -> DocumentReclassifyResponse:
    """Re-run classifier em todos (ou não-overridados) os docs do workspace.

    Útil quando regras do classifier mudam ou docs foram subidos com extensão
    errada. Não reprocessa JSONs de members/baseline (classificados por estrutura).
    """
    stats = await reclassify_workspace_documents(
        workspace.id,
        repo=repo,
        storage=_storage,
        skip_manual_overrides=skip_manual_overrides,
    )
    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=workspace.id,
            aggregate_type="workspace",
            workspace_id=workspace.id,
            action=AuditAction.document_update_classification.value,
            resource_type="workspace",
            resource_id=workspace.id,
            actor_user_id=current_user.id,
            ip_address=ip,
            user_agent=ua,
            details={
                "total": stats.total,
                "updated": stats.updated,
                "skipped": stats.skipped,
                "errors": stats.errors,
            },
        ),
        {"db": db},
    )
    await db.commit()
    return DocumentReclassifyResponse(
        total=stats.total,
        updated=stats.updated,
        skipped=stats.skipped,
        errors=stats.errors,
    )
