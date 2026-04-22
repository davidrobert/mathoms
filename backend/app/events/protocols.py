"""Tipos compartilhados pelo dispatcher e handlers (ADR-115)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeAlias, TypedDict, TypeVar

from backend.app.events.base import Event

if TYPE_CHECKING:  # pragma: no cover - só para type hints
    from sqlalchemy.ext.asyncio import AsyncSession


class EventHandlerDeps(TypedDict, total=False):
    """Dependências que o dispatcher injeta nos handlers em tempo de dispatch.

    ``total=False`` porque a maioria dos handlers consome apenas um subset —
    ``write_audit_entry`` precisa de ``db``; um handler futuro que apenas
    log-a métricas não precisa de nada.
    """

    db: "AsyncSession"


EventT = TypeVar("EventT", bound=Event, contravariant=True)

# Aliases tipados para handlers concretos. ``EventT`` é contravariant
# porque handlers são funções que *consomem* o evento (input-position).
SyncHandler: TypeAlias = Callable[[EventT, EventHandlerDeps], None]
AsyncHandler: TypeAlias = Callable[[EventT, EventHandlerDeps], Awaitable[None]]

# Internal registry storage — não use em assinaturas de handler. O
# dispatcher identifica sync vs async em runtime via ``iscoroutine``
# porque ``Callable[..., None | Awaitable[None]]`` é exatamente o que
# descreve a união das duas formas permitidas.
AnyHandler: TypeAlias = Callable[..., None] | Callable[..., Awaitable[None]]
