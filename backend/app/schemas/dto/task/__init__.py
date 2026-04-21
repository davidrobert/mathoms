"""DTOs do agregado ``Task`` (+ sub-agregados ``TaskAttachment``,
``TaskSuggestion``) — ADR-074.

Re-exports convenientes — prefira estes imports ao invés de alcançar
módulos internos, para manter o pacote como fronteira do agregado.
"""

from backend.app.schemas.dto.task.attachment import (
    TaskAttachmentListResponse,
    TaskAttachmentResponse,
)
from backend.app.schemas.dto.task.command import (
    TaskCreateCommand,
    TaskStatusTransitionCommand,
    TaskUpdateCommand,
)
from backend.app.schemas.dto.task.filters import TaskFilters
from backend.app.schemas.dto.task.mapper import (
    task_attachment_to_response,
    task_suggestion_to_response,
    task_to_response,
)
from backend.app.schemas.dto.task.progress import TaskProgressResponse
from backend.app.schemas.dto.task.response import (
    ScanDeadlinesResponse,
    TaskBase,
    TaskListResponse,
    TaskResponse,
)
from backend.app.schemas.dto.task.suggestion import (
    TaskSuggestionApproveCommand,
    TaskSuggestionCreateCommand,
    TaskSuggestionListResponse,
    TaskSuggestionProposed,
    TaskSuggestionRejectCommand,
    TaskSuggestionResponse,
)
from backend.app.schemas.dto.task.types import (
    CreatedFrom,
    DeadlineKind,
    Priority,
    SuggestionSource,
    SuggestionStatus,
    TaskStatus,
)

__all__ = [
    "CreatedFrom",
    "DeadlineKind",
    "Priority",
    "ScanDeadlinesResponse",
    "SuggestionSource",
    "SuggestionStatus",
    "TaskAttachmentListResponse",
    "TaskAttachmentResponse",
    "TaskBase",
    "TaskCreateCommand",
    "TaskFilters",
    "TaskListResponse",
    "TaskProgressResponse",
    "TaskResponse",
    "TaskStatus",
    "TaskStatusTransitionCommand",
    "TaskSuggestionApproveCommand",
    "TaskSuggestionCreateCommand",
    "TaskSuggestionListResponse",
    "TaskSuggestionProposed",
    "TaskSuggestionRejectCommand",
    "TaskSuggestionResponse",
    "TaskUpdateCommand",
    "task_attachment_to_response",
    "task_suggestion_to_response",
    "task_to_response",
]
