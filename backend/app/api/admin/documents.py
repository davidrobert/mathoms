"""Admin routes — documents (purge bulk + exclusão individual)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.internal_ops_auth import (
    InternalOpsPrincipal,
    require_internal_operator,
)
from backend.app.schemas.admin import (
    DeleteDocumentResponse,
    PurgeDocumentsRequest,
    PurgeDocumentsResponse,
    ScopeContextDTO,
)
from backend.app.services.internal_ops import PurgeScope, delete_document, purge_documents

router = APIRouter(prefix="/documents")


def _partial_failure_exception(details: dict) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "code": "partial_failure",
            "count": details["count"],
            "ids": list(details["ids"]),
            "failed_blobs": list(details["failed_blobs"]),
            "blobs_removed": details["blobs_removed"],
        },
    )


def _to_purge_response(details: dict) -> PurgeDocumentsResponse:
    ctx_raw = details.get("scope_context") or {}
    return PurgeDocumentsResponse(
        preview=details["preview"],
        count=details["count"],
        ids=list(details["ids"]),
        runs_to_remove=details.get("runs_to_remove", 0),
        runs_removed=details.get("runs_removed"),
        blobs_removed=details.get("blobs_removed"),
        scope_context=ScopeContextDTO(
            owner_email=ctx_raw.get("owner_email"),
            workspace_names=list(ctx_raw.get("workspace_names") or []),
        ),
    )


@router.post("/purge", response_model=PurgeDocumentsResponse)
async def purge(
    body: PurgeDocumentsRequest,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> PurgeDocumentsResponse:
    if not body.user_id and not body.workspace_id:
        raise HTTPException(status_code=422, detail="scope_required")
    result = await purge_documents(
        db,
        scope=PurgeScope(user_id=body.user_id, workspace_id=body.workspace_id),
        actor=principal.actor,
        preview=body.preview,
    )
    if not result.ok:
        if result.error == "partial_failure":
            raise _partial_failure_exception(result.details)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)
    await db.commit()
    return _to_purge_response(result.details)


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
async def delete_one(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> DeleteDocumentResponse:
    result = await delete_document(db, document_id, actor=principal.actor)
    if not result.ok:
        code = (
            status.HTTP_404_NOT_FOUND
            if result.error == "document_not_found"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=result.error)
    await db.commit()
    return DeleteDocumentResponse(
        document_id=result.details["document_id"],
        blob_removed=result.details["blob_removed"],
    )
