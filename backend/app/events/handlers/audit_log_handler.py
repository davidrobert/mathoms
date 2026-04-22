"""Handler: escreve ``AuditLog`` na transação atual (A6e.events · slice 2).

Consome ``AuditLogEvent`` e também ``FamilyMemberCreatedEvent`` — este
último é traduzido para ``AuditLogEvent`` internamente. Padrão replicável
para outros eventos de agregados que precisam de audit (Task, Goal…).
"""

from __future__ import annotations

from backend.app.events.domain import AuditLogEvent, FamilyMemberCreatedEvent
from backend.app.events.protocols import EventHandlerDeps
from backend.app.events.registry import register_handler
from backend.app.models.audit_log import AuditLog


@register_handler(AuditLogEvent)
async def write_audit_entry(event: AuditLogEvent, deps: EventHandlerDeps) -> None:
    """Persiste ``AuditLog`` usando a sessão injetada — sem commit próprio.

    Levanta ``KeyError`` se o caller não injetou ``db`` — falha ruidosa é
    o contrato (ADR-111 não permite fallback a global).
    """
    db = deps["db"]
    entry = AuditLog(
        workspace_id=event.workspace_id,
        actor_user_id=event.actor_user_id,
        action=event.action,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        ip_address=event.ip_address,
        user_agent=event.user_agent,
        details=event.details,
        created_at=event.occurred_at,
    )
    db.add(entry)
    await db.flush()


@register_handler(FamilyMemberCreatedEvent)
async def audit_family_member_created(
    event: FamilyMemberCreatedEvent, deps: EventHandlerDeps
) -> None:
    """Traduz ``FamilyMemberCreatedEvent`` para ``AuditLogEvent``.

    Mantém o audit entry livre do payload cru do agregado (nome completo
    fica em ``details.member_key`` e ``resource_id`` = id do membro).
    """
    audit = AuditLogEvent(
        aggregate_id=event.aggregate_id,
        aggregate_type=event.aggregate_type,
        workspace_id=event.workspace_id,
        occurred_at=event.occurred_at,
        action="family_member.created",
        resource_type="family_member",
        resource_id=event.member_id,
        actor_user_id=event.actor_user_id,
        details={"member_key": event.member_key},
    )
    await write_audit_entry(audit, deps)
