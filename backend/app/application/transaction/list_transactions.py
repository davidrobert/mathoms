"""Use case: lista transações paginadas + summary."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.transaction._loading import load_filtered_transactions
from backend.app.application.transaction.filters import TransactionFilters
from backend.app.schemas.transactions import TransactionListResponse
from backend.app.services.transaction_service import paginate_transactions


async def list_transactions(
    workspace_id: str,
    filters: TransactionFilters,
    *,
    page: int,
    page_size: int,
    db: AsyncSession,
) -> TransactionListResponse:
    transactions = await load_filtered_transactions(workspace_id, filters, db=db)
    page_items, summary = paginate_transactions(transactions, page, page_size)
    return TransactionListResponse(
        transactions=page_items,
        total=summary.count,
        page=page,
        page_size=page_size,
        summary=summary,
    )
