"""Transactions API — list, filter, and override categorized transactions from E4 JSON (tenant-scoped, ADR-072)."""

from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.transaction_override import TransactionOverride
from backend.app.models.workspace import Workspace
from backend.app.schemas.transactions import (
    TransactionListResponse,
    TransactionOverrideRequest,
    TransactionOverrideResponse,
)
from backend.app.services.transaction_service import (
    apply_overrides,
    filter_transactions,
    load_transactions,
    paginate_transactions,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/transactions",
    tags=["transactions"],
)


def _tenant_root(workspace_id: str) -> str:
    return str(settings.STORAGE_ROOT / workspace_id)


async def _load_overrides_map(ws_id: str, db: AsyncSession) -> dict[str, TransactionOverride]:
    result = await db.execute(
        select(TransactionOverride).where(TransactionOverride.workspace_id == ws_id)
    )
    return {o.transaction_hash: o for o in result.scalars().all()}


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    member: Optional[str] = Query(None),
    bank: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    value_min: Optional[float] = Query(None),
    value_max: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    transactions = load_transactions(_tenant_root(workspace.id))
    overrides_map = await _load_overrides_map(workspace.id, db)
    transactions = apply_overrides(transactions, overrides_map)

    transactions = filter_transactions(
        transactions,
        member=member,
        bank=bank,
        category=category,
        date_from=date_from,
        date_to=date_to,
        value_min=value_min,
        value_max=value_max,
        search=search,
    )

    page_items, summary = paginate_transactions(transactions, page, page_size)

    return TransactionListResponse(
        transactions=page_items,
        total=summary.count,
        page=page,
        page_size=page_size,
        summary=summary,
    )


@router.get(
    "/export",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "CSV com BOM (UTF-8) — transações filtradas.",
            "content": {"text/csv": {}},
        },
    },
)
async def export_transactions(
    member: Optional[str] = Query(None),
    bank: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    value_min: Optional[float] = Query(None),
    value_max: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    format: str = Query("csv", pattern=r"^(csv)$"),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """BUG-009 fix: export ALL filtered transactions server-side (no pagination).

    Returns a CSV download with BOM for Excel compatibility.
    """
    transactions = load_transactions(_tenant_root(workspace.id))
    overrides_map = await _load_overrides_map(workspace.id, db)
    transactions = apply_overrides(transactions, overrides_map)

    transactions = filter_transactions(
        transactions,
        member=member,
        bank=bank,
        category=category,
        date_from=date_from,
        date_to=date_to,
        value_min=value_min,
        value_max=value_max,
        search=search,
    )

    buf = io.StringIO()
    # UTF-8 BOM for Excel
    buf.write("\ufeff")
    writer = csv.writer(buf)
    writer.writerow(["Data", "Descrição", "Categoria", "Valor", "Membro", "Banco", "Origem", "Editado"])
    for tx in transactions:
        writer.writerow([
            tx.data,
            tx.descricao,
            tx.categoria,
            tx.valor,
            tx.membro,
            tx.banco,
            tx.origem,
            "Sim" if tx.reviewed else "",
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="transacoes.csv"'},
    )


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
):
    transactions = load_transactions(_tenant_root(workspace.id))
    matching = [t for t in transactions if t.transaction_hash == transaction_hash]
    if not matching:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    original_category = matching[0].categoria

    result = await db.execute(
        select(TransactionOverride).where(
            TransactionOverride.workspace_id == workspace.id,
            TransactionOverride.transaction_hash == transaction_hash,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.new_category = body.new_category
        existing.notes = body.notes
        existing.reviewed = True
        await db.commit()
        await db.refresh(existing)
        return TransactionOverrideResponse.model_validate(existing)

    override = TransactionOverride(
        workspace_id=workspace.id,
        transaction_hash=transaction_hash,
        original_category=original_category,
        new_category=body.new_category,
        notes=body.notes,
        reviewed=True,
    )
    db.add(override)
    await db.commit()
    await db.refresh(override)
    return TransactionOverrideResponse.model_validate(override)


@router.delete(
    "/{transaction_hash}/override",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_role)],
)
async def delete_override(
    transaction_hash: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TransactionOverride).where(
            TransactionOverride.workspace_id == workspace.id,
            TransactionOverride.transaction_hash == transaction_hash,
        )
    )
    override = result.scalar_one_or_none()
    if not override:
        raise HTTPException(status_code=404, detail="Override não encontrado")
    await db.delete(override)
    await db.commit()
