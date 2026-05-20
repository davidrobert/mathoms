"""DebtRepository — CRUD async para Debt (ADR-227 §D1); todo método predicado por ``workspace_id``."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.debt import Debt


class DebtRepository:
    """Single Responsibility: persistência do agregado ``Debt``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def list_for_workspace(self, workspace_id: str) -> list[Debt]:
        """Todas as Debts do workspace, ordenadas por ``created_at`` ASC."""
        result = await self._session.execute(
            select(Debt).where(Debt.workspace_id == workspace_id).order_by(Debt.created_at, Debt.id)
        )
        return list(result.scalars().all())

    async def list_for_property(self, workspace_id: str, property_id: str) -> list[Debt]:
        """Debts vinculadas a um imóvel específico."""
        result = await self._session.execute(
            select(Debt)
            .where(
                Debt.workspace_id == workspace_id,
                Debt.property_id == property_id,
            )
            .order_by(Debt.created_at, Debt.id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, workspace_id: str, debt_id: str) -> Optional[Debt]:
        """Debt por id dentro do workspace; ``None`` se não existe."""
        result = await self._session.execute(
            select(Debt).where(
                Debt.id == debt_id,
                Debt.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_needs_review(self, workspace_id: str) -> list[Debt]:
        """Debts pendentes de revisão humana (Onda 2 + Onda 5 batch review)."""
        result = await self._session.execute(
            select(Debt)
            .where(
                Debt.workspace_id == workspace_id,
                Debt.needs_review.is_(True),
            )
            .order_by(Debt.created_at, Debt.id)
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------

    async def create(self, workspace_id: str, **fields: Any) -> Debt:
        """Cria Debt e retorna instância persistida."""
        debt = Debt(workspace_id=workspace_id, **fields)
        self._session.add(debt)
        await self._session.commit()
        await self._session.refresh(debt)
        return debt

    async def update(self, debt: Debt, **fields: Any) -> Debt:
        """Aplica updates em ``debt`` e devolve com refresh."""
        for k, v in fields.items():
            setattr(debt, k, v)
        await self._session.commit()
        await self._session.refresh(debt)
        return debt

    async def delete(self, debt: Debt) -> None:
        """Remove a Debt (caller resolveu RESTRICT se property_id NOT NULL)."""
        await self._session.delete(debt)
        await self._session.commit()

    async def bulk_create_from_migration(self, rows: Iterable[dict[str, Any]]) -> int:
        """Insert em batch para backfill (Onda 2); idempotência via ``uq_debt_migration_source``."""
        debts = [Debt(**row) for row in rows]
        self._session.add_all(debts)
        await self._session.commit()
        return len(debts)
