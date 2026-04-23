"""Transactions router fino — list/export/override (A6e.4 · ADR-101 R15/R16)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.transaction import (
    TransactionFilters,
)
from backend.app.application.transaction import (
    create_override as _create_override,
)
from backend.app.application.transaction import (
    delete_override as _delete_override,
)
from backend.app.application.transaction import (
    export_transactions_csv as _export_csv,
)
from backend.app.application.transaction import (
    list_transactions as _list_transactions,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.workspace import Workspace
from backend.app.schemas.transactions import (
    TransactionListResponse,
    TransactionOverrideRequest,
    TransactionOverrideResponse,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/transactions",
    tags=["transactions"],
)


def _filters(
    member: str | None = Query(None),
    bank: str | None = Query(None),
    category: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    value_min: float | None = Query(None),
    value_max: float | None = Query(None),
    search: str | None = Query(None),
) -> TransactionFilters:
    return TransactionFilters(
        member=member,
        bank=bank,
        category=category,
        date_from=date_from,
        date_to=date_to,
        value_min=value_min,
        value_max=value_max,
        search=search,
    )


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    filters: TransactionFilters = Depends(_filters),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    return await _list_transactions(workspace.id, filters, page=page, page_size=page_size, db=db)


@router.get(
    "/export",
    response_class=StreamingResponse,
    responses={200: {"description": "CSV com BOM (UTF-8).", "content": {"text/csv": {}}}},
)
async def export_transactions(
    filters: TransactionFilters = Depends(_filters),
    format: str = Query("csv", pattern=r"^(csv)$"),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    return await _export_csv(workspace.id, filters, db=db)


@router.post(
    "/{transaction_hash}/override",
    response_model=TransactionOverrideResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_role)],
)
async def create_override(
    transaction_hash: str,
    body: TransactionOverrideRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> TransactionOverrideResponse:
    return await _create_override(workspace.id, transaction_hash, body, db=db)


@router.delete(
    "/{transaction_hash}/override",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_role)],
)
async def delete_override(
    transaction_hash: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _delete_override(workspace.id, transaction_hash, db=db)
