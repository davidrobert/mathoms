"""Classes de domain events concretos (ADR-115).

Novos eventos entram aqui com ``@dataclass(frozen=True, slots=True,
kw_only=True)``. Campos herdados de ``Event`` (``event_id``,
``occurred_at``, ``aggregate_id``, ``aggregate_type``, ``workspace_id``)
já têm defaults — subclasses podem declarar campos obrigatórios sem
colidir com a regra "defaulted fields must follow non-defaulted".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.events.base import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditLogEvent(Event):
    """Solicita registro de uma linha em ``audit_logs`` (F6.5).

    Emitido por use cases que precisam deixar trilha auditável. O handler
    ``write_audit_entry`` consome e persiste — o caller continua dono da
    transação (``db.commit()`` não é feito pelo handler).
    """

    action: str = ""
    resource_type: str = ""
    resource_id: str | None = None
    actor_user_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FamilyMemberCreatedEvent(Event):
    """Membro da família criado (A6e.events — primeiro caso migrado).

    ``member_name`` viaja cru no evento mas **nunca** deve ir para log
    não-estruturado (ADR-110 §mascaramento de PII). Handlers são
    responsáveis por transformar para forma apropriada do destino
    (audit entry redige; notificação mascara; métrica descarta).
    """

    member_id: str = ""
    member_key: str = ""
    member_name: str = ""
    actor_user_id: str | None = None
