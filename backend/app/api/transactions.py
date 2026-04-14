"""Transactions API — list, filter, and override categorized transactions from E4 JSON."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.transaction_override import TransactionOverride
from backend.app.models.user import User
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

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def _get_workspace(user: User, db: AsyncSession) -> Workspace:
    result = await db.execute(select(Workspace).where(Workspace.owner_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    return ws


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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    transactions = load_transactions(_tenant_root(ws.id))
    overrides_map = await _load_overrides_map(ws.id, db)
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


@router.post(
    "/{transaction_hash}/override",
    response_model=TransactionOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_override(
    transaction_hash: str,
    body: TransactionOverrideRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)

    transactions = load_transactions(_tenant_root(ws.id))
    matching = [t for t in transactions if t.transaction_hash == transaction_hash]
    if not matching:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    original_category = matching[0].categoria

    result = await db.execute(
        select(TransactionOverride).where(
            TransactionOverride.workspace_id == ws.id,
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
        workspace_id=ws.id,
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


@router.delete("/{transaction_hash}/override", status_code=status.HTTP_204_NO_CONTENT)
async def delete_override(
    transaction_hash: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(TransactionOverride).where(
            TransactionOverride.workspace_id == ws.id,
            TransactionOverride.transaction_hash == transaction_hash,
        )
    )
    override = result.scalar_one_or_none()
    if not override:
        raise HTTPException(status_code=404, detail="Override não encontrado")
    await db.delete(override)
    await db.commit()
