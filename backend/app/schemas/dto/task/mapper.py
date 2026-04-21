"""Mapper ORM → DTO para o agregado ``Task`` e sub-agregados.

Os três mappers são equivalentes a ``DTO.model_validate(orm)`` pelo
``from_attributes=True``, mas a função nomeada é preferível pelo
mesmo motivo dos outros slices A6e:

1. Simétrico aos outros agregados (category, family_member, document,
   config_blob, goal).
2. Ponto único para futuras divergências DTO ↔ ORM.
3. Testável sem instanciar validator Pydantic no teste.
"""

from __future__ import annotations

from backend.app.models.task import Task, TaskAttachment, TaskSuggestion
from backend.app.schemas.dto.task.attachment import TaskAttachmentResponse
from backend.app.schemas.dto.task.response import TaskResponse
from backend.app.schemas.dto.task.suggestion import TaskSuggestionResponse


def task_to_response(task: Task) -> TaskResponse:
    """Converte ORM ``Task`` → DTO de resposta."""
    return TaskResponse.model_validate(task)


def task_attachment_to_response(
    attachment: TaskAttachment,
) -> TaskAttachmentResponse:
    """Converte ORM ``TaskAttachment`` → DTO de resposta (só metadata)."""
    return TaskAttachmentResponse.model_validate(attachment)


def task_suggestion_to_response(
    suggestion: TaskSuggestion,
) -> TaskSuggestionResponse:
    """Converte ORM ``TaskSuggestion`` → DTO de resposta."""
    return TaskSuggestionResponse.model_validate(suggestion)
