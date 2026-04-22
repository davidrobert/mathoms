"""Use cases do agregado ``Notification`` (ADR-072 · ADR-101 R15).

Persistência de eventos workspace-level consumidos pela UI (badge +
drawer). Lógica de geração de notificação continua em
:mod:`backend.app.services.task_notification_service` e similares.
"""

from backend.app.application.notification.delete_notification import (
    delete_notification,
)
from backend.app.application.notification.list_notifications import (
    list_notifications,
)
from backend.app.application.notification.mark_notifications_read import (
    mark_notifications_read,
)

__all__ = [
    "delete_notification",
    "list_notifications",
    "mark_notifications_read",
]
