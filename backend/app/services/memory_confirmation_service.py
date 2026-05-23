"""Memory confirmation service (ADR-262): endosse + stale detection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workspace_memory_confirmation import WorkspaceMemoryConfirmation
from backend.app.repositories.workspace_memory_confirmation_repository import (
    WorkspaceMemoryConfirmationRepository,
    is_stale_by_age,
    is_stale_by_value,
)


@dataclass(frozen=True)
class MemoryStatus:
    """Estado de uma `memory_key` projetado em Memories surface 3.E."""

    memory_key: str
    confirmed: bool
    confirmed_at: Optional[datetime]
    confirmed_by_user_id: Optional[str]
    stale: bool
    stale_reason: Optional[str]  # "age" | "value" | None


async def confirm(
    workspace_id: str,
    memory_key: str,
    source_aggregate: str,
    *,
    db: AsyncSession,
    user_id: Optional[str] = None,
    snapshot: Optional[str] = None,
    note: Optional[str] = None,
) -> WorkspaceMemoryConfirmation:
    """Registra confirmação append-only. Caller é dono da transação (commit fora)."""
    repo = WorkspaceMemoryConfirmationRepository(db)
    return await repo.create(
        workspace_id,
        memory_key,
        source_aggregate,
        confirmed_value_snapshot=snapshot,
        confirmed_by_user_id=user_id,
        note=note,
    )


_UNCONFIRMED_STATUS_KWARGS = dict(
    confirmed=False, confirmed_at=None, confirmed_by_user_id=None, stale=False, stale_reason=None
)


def _build_status(
    memory_key: str,
    latest: Optional[WorkspaceMemoryConfirmation] = None,
    current_value: Optional[str] = None,
    now: Optional[datetime] = None,
) -> MemoryStatus:
    if latest is None:
        return MemoryStatus(memory_key=memory_key, **_UNCONFIRMED_STATUS_KWARGS)
    stale_age = is_stale_by_age(latest.confirmed_at, now=now)
    stale_val = is_stale_by_value(latest.confirmed_value_snapshot, current_value)
    reason = "age" if stale_age else ("value" if stale_val else None)
    return MemoryStatus(
        memory_key=memory_key,
        confirmed=not (stale_age or stale_val),
        confirmed_at=latest.confirmed_at,
        confirmed_by_user_id=latest.confirmed_by_user_id,
        stale=stale_age or stale_val,
        stale_reason=reason,
    )


async def get_status(
    workspace_id: str,
    memory_key: str,
    current_value: Optional[str] = None,
    *,
    db: AsyncSession,
    now: Optional[datetime] = None,
) -> MemoryStatus:
    """Calcula status (confirmed/stale) para uma `memory_key` cruzando com aggregate de origem."""
    repo = WorkspaceMemoryConfirmationRepository(db)
    latest = await repo.get_latest(workspace_id, memory_key)
    return _build_status(memory_key, latest, current_value, now or datetime.now(timezone.utc))
