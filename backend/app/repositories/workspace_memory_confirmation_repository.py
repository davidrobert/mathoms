"""CRUD async para `WorkspaceMemoryConfirmation` (append-only). ADR-262."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workspace_memory_confirmation import WorkspaceMemoryConfirmation


class WorkspaceMemoryConfirmationRepository:
    """Persistência da tabela `workspace_memory_confirmations` (ADR-262). R13 ws-scoped, R14 não commita."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(
        self, workspace_id: str, memory_key: str
    ) -> Optional[WorkspaceMemoryConfirmation]:
        """Retorna a confirmação mais recente para `(workspace_id, memory_key)`."""
        result = await self._session.execute(
            select(WorkspaceMemoryConfirmation)
            .where(
                WorkspaceMemoryConfirmation.workspace_id == workspace_id,
                WorkspaceMemoryConfirmation.memory_key == memory_key,
            )
            .order_by(WorkspaceMemoryConfirmation.confirmed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: str) -> list[WorkspaceMemoryConfirmation]:
        """Lista todas as confirmações do workspace, mais recente primeiro."""
        result = await self._session.execute(
            select(WorkspaceMemoryConfirmation)
            .where(WorkspaceMemoryConfirmation.workspace_id == workspace_id)
            .order_by(WorkspaceMemoryConfirmation.confirmed_at.desc())
        )
        return list(result.scalars().all())

    async def list_history(
        self, workspace_id: str, memory_key: str
    ) -> list[WorkspaceMemoryConfirmation]:
        """Histórico completo de confirmações de uma `memory_key`."""
        result = await self._session.execute(
            select(WorkspaceMemoryConfirmation)
            .where(
                WorkspaceMemoryConfirmation.workspace_id == workspace_id,
                WorkspaceMemoryConfirmation.memory_key == memory_key,
            )
            .order_by(WorkspaceMemoryConfirmation.confirmed_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        workspace_id: str,
        memory_key: str,
        source_aggregate: str,
        **kwargs,
    ) -> WorkspaceMemoryConfirmation:
        """Cria nova confirmação (append-only). Kwargs: confirmed_value_snapshot, confirmed_by_user_id, note, confirmed_at."""
        kwargs.setdefault("confirmed_at", datetime.now(timezone.utc))
        row = WorkspaceMemoryConfirmation(
            workspace_id=workspace_id,
            memory_key=memory_key,
            source_aggregate=source_aggregate,
            **kwargs,
        )
        self._session.add(row)
        await self._session.flush()
        return row


# ── Stale detection (ADR-262 §Invalidação de confirmação) ──────────────


STALE_AGE_DAYS = 365
STALE_RELATIVE_THRESHOLD = 0.02  # 2% absoluto p/ valores numéricos


def _ensure_utc(dt: datetime) -> datetime:
    """Coerce naive datetime → UTC-aware (SQLite returns naive; Postgres returns aware)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def is_stale_by_age(
    confirmed_at: datetime, *, now: Optional[datetime] = None, max_age_days: int = STALE_AGE_DAYS
) -> bool:
    """True se confirmação tem ≥`max_age_days` (default 12 meses)."""
    reference = _ensure_utc(now) if now else datetime.now(timezone.utc)
    return (reference - _ensure_utc(confirmed_at)) >= timedelta(days=max_age_days)


def is_stale_by_value(
    snapshot: Optional[str] = None,
    current: Optional[str] = None,
    *,
    relative_threshold: float = STALE_RELATIVE_THRESHOLD,
) -> bool:
    """True se `current` divergiu de `snapshot` (numérico: ≥`relative_threshold`; categórico: qualquer diff)."""
    if snapshot is None or current is None:
        return True
    if snapshot == current:
        return False
    try:
        snap_v = float(snapshot)
        curr_v = float(current)
    except (TypeError, ValueError):
        return True  # categórico — qualquer diff
    if snap_v == 0:
        return curr_v != 0
    return abs(curr_v - snap_v) / abs(snap_v) >= relative_threshold
