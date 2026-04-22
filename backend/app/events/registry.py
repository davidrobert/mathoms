"""Registro estático de handlers por tipo de evento (ADR-115).

Handlers são registrados via decorator ``@register_handler(EventClass)``
em tempo de import — o registro é populado uma única vez no startup do
módulo, equivalente a um singleton idempotente (ADR-111 permite).

Nenhuma descoberta automática por glob: cada módulo de handler deve ser
importado explicitamente em ``backend.app.events.handlers.__init__``
para que seu ``@register_handler`` execute.
"""

from __future__ import annotations

from collections.abc import Callable

from backend.app.events.base import Event
from backend.app.events.protocols import AnyHandler

_HANDLERS: dict[type[Event], list[AnyHandler]] = {}


def register_handler(
    event_class: type[Event],
) -> Callable[[AnyHandler], AnyHandler]:
    """Decorator que adiciona ``handler`` à lista do tipo ``event_class``.

    Ordem de registro = ordem de disparo pelo dispatcher. Handlers
    registrados posteriormente rodam depois; dentro do mesmo evento a
    ordem é estável e determinística.
    """

    def _decorator(handler: AnyHandler) -> AnyHandler:
        _HANDLERS.setdefault(event_class, []).append(handler)
        return handler

    return _decorator


def handlers_for(event_class: type[Event]) -> list[AnyHandler]:
    """Cópia da lista de handlers registrados para ``event_class``."""
    return list(_HANDLERS.get(event_class, ()))


def clear_handlers() -> None:
    """Esvazia o registro — uso exclusivo em testes.

    Evita poluição entre casos quando um teste instala um handler
    temporário. Nunca chamar em produção.
    """
    _HANDLERS.clear()
