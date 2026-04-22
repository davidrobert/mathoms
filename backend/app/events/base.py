"""Base ``Event`` — dataclass imutável para domain events (ADR-115)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


def _new_event_id() -> str:
    return uuid4().hex


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    """Raiz de todos os domain events emitidos por use cases.

    Subclasses adicionam campos de payload; todos os campos herdados têm
    default para permitir que subclasses declarem campos obrigatórios sem
    colidir com a regra "defaulted fields must follow non-defaulted".

    Imutabilidade (``frozen=True``) garante que múltiplos handlers vejam
    sempre o mesmo payload — fundamental para debugabilidade em cascata.
    ``slots=True`` fecha o objeto para atributos ad-hoc; qualquer tentativa
    de mutação levanta ``FrozenInstanceError`` em tempo de execução.
    """

    event_id: str = field(default_factory=_new_event_id)
    occurred_at: datetime = field(default_factory=_now_utc)
    aggregate_id: str | None = None
    aggregate_type: str | None = None
    workspace_id: str | None = None
