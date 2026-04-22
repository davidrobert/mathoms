"""Use cases do agregado ``Task`` (ADR-101 R15 · ADR-074).

Task + sub-agregados ``TaskSuggestion`` e ``TaskAttachment``. Endpoints
de ``/workspaces/{id}/tasks/*`` e ``/task-suggestions/*`` delegam a este
módulo. Composites que envolvem Storage (upload/download de anexo),
export markdown (pure read) e scan de notificações (cross-aggregate
Notification) seguem no router/service por ora — ver ADR-112.

Grafo de transições (`ALLOWED_TRANSITIONS`) vive em ``_rules.py`` —
fonte de verdade do novo layer. A cópia em
``backend.app.services.task_service`` sobrevive apenas enquanto o router
legado estiver em uso (até A6e.4 4b).
"""

from backend.app.application.task.approve_task_suggestion import (
    approve_task_suggestion,
)
from backend.app.application.task.cancel_task import cancel_task
from backend.app.application.task.create_task import create_task
from backend.app.application.task.create_task_suggestion import (
    create_task_suggestion,
)
from backend.app.application.task.delete_task_attachment import (
    delete_task_attachment,
)
from backend.app.application.task.get_task import get_task
from backend.app.application.task.list_task_attachments import (
    list_task_attachments,
)
from backend.app.application.task.list_task_suggestions import (
    list_task_suggestions,
)
from backend.app.application.task.list_workspace_tasks import (
    list_workspace_tasks,
)
from backend.app.application.task.merge_suggestion_into_task import (
    merge_suggestion_into_task,
)
from backend.app.application.task.reject_task_suggestion import (
    reject_task_suggestion,
)
from backend.app.application.task.transition_task_status import (
    transition_task_status,
)
from backend.app.application.task.update_task import update_task

__all__ = [
    "approve_task_suggestion",
    "cancel_task",
    "create_task",
    "create_task_suggestion",
    "delete_task_attachment",
    "get_task",
    "list_task_attachments",
    "list_task_suggestions",
    "list_workspace_tasks",
    "merge_suggestion_into_task",
    "reject_task_suggestion",
    "transition_task_status",
    "update_task",
]
