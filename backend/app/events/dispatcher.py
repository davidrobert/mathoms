"""Dispatcher de domain events — síncrono (em transação) e stub async (ADR-115).

``dispatch_sync`` é a API principal: roda todos os handlers registrados
para ``type(event)`` **na transação do use case chamador**. Qualquer
exceção propaga e o caller pode fazer rollback. Handlers async são
aguardados; handlers sync são invocados diretamente.

``enqueue_async`` é um stub que documenta o caminho pós-commit (Celery /
after_commit listener) mas não implementa — será ativado quando houver
caso concreto (ADR-115 §Escopo futuro).
"""

from __future__ import annotations

import inspect

from backend.app.events.base import Event
from backend.app.events.protocols import EventHandlerDeps
from backend.app.events.registry import handlers_for


async def dispatch_sync(
    event: Event,
    deps: EventHandlerDeps | None = None,
) -> None:
    """Invoca todos os handlers de ``type(event)`` em ordem de registro.

    Handlers rodam dentro da transação atual — falha de qualquer handler
    propaga e o chamador (use case) decide o rollback. Eventos cujo tipo
    não tem handler registrado são silenciosamente ignorados.
    """
    payload: EventHandlerDeps = deps or EventHandlerDeps()
    for handler in handlers_for(type(event)):
        result = handler(event, payload)
        if inspect.isawaitable(result):
            await result


def enqueue_async(event: Event) -> None:
    """Ponte para dispatch pós-commit (Celery / SQLAlchemy after_commit).

    Stub intencional — será implementado quando aparecer o primeiro caso
    concreto de handler que escreve fora do DB (email, broadcast WS).
    Chamar agora levanta ``NotImplementedError`` para forçar decisão
    explícita antes de ativar o caminho async.
    """
    raise NotImplementedError(
        "enqueue_async pendente de slice dedicado (ADR-115 §Escopo futuro)"
    )
