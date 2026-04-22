"""Handler: cria ``Notification`` reativa para Task com prazo próximo (A6e.events slice 3).

Coexiste em paralelo com ``task_notification_service.scan_and_create_notifications``
(polling cron). Ativo apenas quando ``settings.USE_EVENT_DRIVEN_TASK_NOTIFICATIONS``
é True — flag default False mantém o cron como fonte única até validação
em produção.

Dedupe lightweight via ``Notification.title`` seguindo convenção do
serviço legado (``[#<number>:<bucket>]``) — garante que handler e cron
convergem para o mesmo conjunto de titles e não duplicam durante
coexistência.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.events.domain import TaskCreatedEvent, TaskUpdatedEvent
from backend.app.events.protocols import EventHandlerDeps
from backend.app.events.registry import register_handler
from backend.app.models.notification import Notification

_SOURCE = "task_deadline"


def _bucket_for(days_until: int) -> str | None:
    if days_until < 0:
        return "overdue"
    if days_until <= 3:
        return "urgent"
    if days_until <= 7:
        return "soon"
    return None


_SEVERITY = {
    "overdue": "critical",
    "urgent": "warning",
    "soon": "info",
}


def _title(task_number: int, bucket: str) -> str:
    return f"Prazo da tarefa #{task_number} [#{task_number}:{bucket}]"


def _message(task_title: str, deadline: date, bucket: str, today: date) -> str:
    days = (deadline - today).days
    if bucket == "overdue":
        overdue = -days
        return (
            f'"{task_title}" venceu há {overdue} '
            f"dia{'s' if overdue != 1 else ''} "
            f"(prazo: {deadline.isoformat()})."
        )
    if bucket == "urgent":
        return (
            f'"{task_title}" vence em {days} '
            f"dia{'s' if days != 1 else ''} ({deadline.isoformat()})."
        )
    return f'"{task_title}" vence em {days} dias ({deadline.isoformat()}).'


async def _maybe_create_notification(
    event: TaskCreatedEvent | TaskUpdatedEvent,
    deps: EventHandlerDeps,
    *,
    today: date | None = None,
) -> None:
    if not settings.USE_EVENT_DRIVEN_TASK_NOTIFICATIONS:
        return
    if event.deadline_kind != "HARD_DATE" or event.deadline_date is None:
        return

    today = today or datetime.now().date()
    days_until = (event.deadline_date - today).days
    bucket = _bucket_for(days_until)
    if bucket is None:
        return

    db = deps["db"]
    title = _title(event.task_number, bucket)

    existing = await db.execute(
        select(Notification.id).where(
            Notification.workspace_id == event.workspace_id,
            Notification.source == _SOURCE,
            Notification.title == title,
        )
    )
    if existing.first() is not None:
        return

    notification = Notification(
        workspace_id=event.workspace_id,
        severity=_SEVERITY[bucket],
        title=title,
        message=_message(event.task_title, event.deadline_date, bucket, today),
        source=_SOURCE,
        is_read=False,
    )
    db.add(notification)
    await db.flush()


@register_handler(TaskCreatedEvent)
async def on_task_created(event: TaskCreatedEvent, deps: EventHandlerDeps) -> None:
    await _maybe_create_notification(event, deps)


@register_handler(TaskUpdatedEvent)
async def on_task_updated(event: TaskUpdatedEvent, deps: EventHandlerDeps) -> None:
    await _maybe_create_notification(event, deps)
