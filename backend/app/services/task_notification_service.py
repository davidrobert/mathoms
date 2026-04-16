"""Notificações de prazo de Task (ADR-074 §F8.3 — awareness no dia-a-dia).

Varre as tasks ativas de um workspace procurando:
  - deadline_date HARD_DATE vencido (overdue) → notification severity=critical
  - deadline_date HARD_DATE em ≤3 dias → severity=warning
  - deadline_date HARD_DATE em ≤7 dias → severity=info

Idempotente: marca notificações já criadas via `source='task_deadline'` +
chave `task:{id}:bucket:{bucket_name}` no title/message para deduplicação
lightweight. Chamado manualmente via endpoint OU por worker cron em F8.3+.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.notification import Notification
from backend.app.models.task import Task


_SOURCE = "task_deadline"


def _notification_title(task: Task, bucket: str) -> str:
    """Identificador estável usado para deduplicação (append de marca
    `[#N:bucket]` no final permite detectar duplicatas sem campo extra
    no schema de Notification)."""
    return f"Prazo da tarefa #{task.number} [#{task.number}:{bucket}]"


def _notification_message(task: Task, bucket: str, today: date) -> str:
    if task.deadline_date is None:
        return task.title
    days = (task.deadline_date - today).days
    if bucket == "overdue":
        overdue_days = -days
        return (
            f'"{task.title}" venceu há {overdue_days} '
            f"dia{'s' if overdue_days != 1 else ''} "
            f"(prazo: {task.deadline_date.isoformat()})."
        )
    if bucket == "urgent":
        return (
            f'"{task.title}" vence em {days} '
            f"dia{'s' if days != 1 else ''} ({task.deadline_date.isoformat()})."
        )
    return (
        f'"{task.title}" vence em {days} dias '
        f"({task.deadline_date.isoformat()})."
    )


def _bucket_for(days_until_deadline: int) -> Optional[str]:
    """Classifica a urgência. None = fora do horizonte de alerta."""
    if days_until_deadline < 0:
        return "overdue"
    if days_until_deadline <= 3:
        return "urgent"
    if days_until_deadline <= 7:
        return "soon"
    return None


def _severity_for(bucket: str) -> str:
    return {
        "overdue": "critical",
        "urgent": "warning",
        "soon": "info",
    }[bucket]


async def scan_and_create_notifications(
    workspace_id: str,
    *,
    db: AsyncSession,
    today: Optional[date] = None,
) -> dict[str, int]:
    """Varre tasks ativas do workspace e cria notifications de prazo.

    Retorna dict com contadores:
      {"created": N, "skipped_existing": M, "evaluated": T}
    """
    today = today or date.today()

    # Query: tasks ativas com HARD_DATE dentro de 7d ou overdue.
    horizon = today + timedelta(days=7)
    stmt = select(Task).where(
        Task.workspace_id == workspace_id,
        Task.status.in_(("pending", "in_progress")),
        Task.deadline_kind == "HARD_DATE",
        Task.deadline_date.isnot(None),
        Task.deadline_date <= horizon,
    )
    tasks = list((await db.execute(stmt)).scalars().all())

    # Pré-carrega notifications existentes dessa source/workspace para
    # deduplicação. Escopo pequeno — só pegamos as dos últimos 30 dias.
    # tenancy garantida via workspace_id filter
    existing_stmt = select(Notification).where(
        Notification.workspace_id == workspace_id,
        Notification.source == _SOURCE,
    )
    existing_titles = {
        n.title for n in (await db.execute(existing_stmt)).scalars().all()
    }

    created = 0
    skipped = 0
    for task in tasks:
        if task.deadline_date is None:
            continue
        days_until = (task.deadline_date - today).days
        bucket = _bucket_for(days_until)
        if bucket is None:
            continue

        title = _notification_title(task, bucket)
        if title in existing_titles:
            skipped += 1
            continue

        notification = Notification(
            workspace_id=workspace_id,
            severity=_severity_for(bucket),
            title=title,
            message=_notification_message(task, bucket, today),
            source=_SOURCE,
            is_read=False,
        )
        db.add(notification)
        created += 1

    if created:
        await db.flush()

    return {
        "created": created,
        "skipped_existing": skipped,
        "evaluated": len(tasks),
    }


__all__ = ["scan_and_create_notifications"]
