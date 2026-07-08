"""Domain events tipados — camada de eventos de domínio (A6e.events · ADR-101 R17 · ADR-115).

Emite eventos de use cases em ``backend/app/application/``; handlers
concretos escrevem audit logs, notificações ou enfileiram tarefas async.
Não confundir com ``backend/app/services/pipeline/events.py`` (Redis pub/sub de
progresso de stages do pipeline — escopo diferente).

Ponto de entrada público:

    from backend.app.events import (
        Event,
        EventHandlerDeps,
        dispatch_sync,
        register_handler,
    )
    from backend.app.events.domain import AuditLogEvent, FamilyMemberCreatedEvent

Handlers concretos vivem em ``backend.app.events.handlers`` e são
registrados via decorator ``@register_handler(EventClass)`` — o próprio
import deste pacote dispara o registro (ver ``handlers.__init__``).
"""

from __future__ import annotations

# Import handlers para disparar registros. NÃO remover — sem isto, os
# decoradores nunca rodam e os handlers ficam invisíveis ao dispatcher.
from backend.app.events import handlers as _handlers  # noqa: F401,E402
from backend.app.events.base import Event
from backend.app.events.dispatcher import dispatch_sync, enqueue_async
from backend.app.events.protocols import EventHandlerDeps
from backend.app.events.registry import clear_handlers, register_handler

__all__ = [
    "Event",
    "EventHandlerDeps",
    "clear_handlers",
    "dispatch_sync",
    "enqueue_async",
    "register_handler",
]
