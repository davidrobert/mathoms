"""Legacy shim para ``schemas.task``.

Os DTOs canônicos do agregado ``Task`` vivem em
``backend/app/schemas/dto/task/`` (A6e.7 — ADR-101). Este módulo
re-exporta com os nomes antigos para que:

- testes legados (``from backend.app.schemas.task import TaskResponse``),
  services internos (``task_notification_service``,
  ``task_progress_service``), seed scripts e factory builders
  continuem passando sem modificação;
- integrações externas que possam ter importado esses símbolos não
  quebrem durante a janela de migração.

``*Create`` / ``*Update`` ganharam sufixo ``Command`` na nova
estrutura; ``TaskStatusTransition`` → ``TaskStatusTransitionCommand``;
``TaskSuggestionApprove`` / ``TaskSuggestionReject`` →
``*Command``; ``TaskProgress`` → ``TaskProgressResponse``; ``TaskFilters``
migrou para ``dto/task/filters.py``. Aliases abaixo preservam todos
os imports legados.

Preferir nas chamadas novas::

    from backend.app.schemas.dto.task import (
        TaskResponse, TaskCreateCommand, TaskUpdateCommand, ...
    )
"""

from __future__ import annotations

from backend.app.schemas.dto.task.attachment import (
    TaskAttachmentListResponse,
    TaskAttachmentResponse,
)
from backend.app.schemas.dto.task.command import (
    TaskCreateCommand as TaskCreate,
)
from backend.app.schemas.dto.task.command import (
    TaskStatusTransitionCommand as TaskStatusTransition,
)
from backend.app.schemas.dto.task.command import (
    TaskUpdateCommand as TaskUpdate,
)
from backend.app.schemas.dto.task.filters import TaskFilters
from backend.app.schemas.dto.task.progress import (
    TaskProgressResponse as TaskProgress,
)
from backend.app.schemas.dto.task.response import (
    ScanDeadlinesResponse,
    TaskBase,
    TaskListResponse,
    TaskResponse,
)
from backend.app.schemas.dto.task.suggestion import (
    TaskSuggestionApproveCommand as TaskSuggestionApprove,
)
from backend.app.schemas.dto.task.suggestion import (
    TaskSuggestionCreateCommand as TaskSuggestionCreate,
)
from backend.app.schemas.dto.task.suggestion import (
    TaskSuggestionListResponse,
    TaskSuggestionProposed,
    TaskSuggestionResponse,
)
from backend.app.schemas.dto.task.suggestion import (
    TaskSuggestionRejectCommand as TaskSuggestionReject,
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
    "TaskCreate",
    "TaskFilters",
    "TaskListResponse",
    "TaskProgress",
    "TaskResponse",
    "TaskStatus",
    "TaskStatusTransition",
    "TaskSuggestionApprove",
    "TaskSuggestionCreate",
    "TaskSuggestionListResponse",
    "TaskSuggestionProposed",
    "TaskSuggestionReject",
    "TaskSuggestionResponse",
    "TaskUpdate",
]
