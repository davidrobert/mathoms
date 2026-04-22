"""Integration — ``AuditLogEvent`` handler grava ``AuditLog`` (A6e.events slice 2)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from backend.app.events import dispatch_sync
from backend.app.events.domain import AuditLogEvent, FamilyMemberCreatedEvent
from backend.app.models.audit_log import AuditLog
from backend.tests.factories import make_workspace


@pytest.mark.asyncio
async def test_audit_log_event_persists_row(db):
    ws = await make_workspace(db)

    event = AuditLogEvent(
        workspace_id=ws.id,
        action="test.event",
        resource_type="test",
        resource_id="res-1",
        details={"foo": "bar"},
    )
    await dispatch_sync(event, {"db": db})
    await db.commit()

    rows = (await db.execute(select(AuditLog).where(AuditLog.workspace_id == ws.id))).scalars().all()
    assert len(rows) == 1
    entry = rows[0]
    assert entry.action == "test.event"
    assert entry.resource_type == "test"
    assert entry.resource_id == "res-1"
    assert entry.details == {"foo": "bar"}


@pytest.mark.asyncio
async def test_audit_log_event_preserves_occurred_at(db):
    ws = await make_workspace(db)
    when = datetime(2026, 4, 22, 10, 30, tzinfo=UTC)

    event = AuditLogEvent(
        occurred_at=when,
        workspace_id=ws.id,
        action="test.event",
        resource_type="test",
    )
    await dispatch_sync(event, {"db": db})
    await db.commit()

    entry = (await db.execute(select(AuditLog).where(AuditLog.workspace_id == ws.id))).scalar_one()
    assert entry.created_at.replace(tzinfo=UTC) == when


@pytest.mark.asyncio
async def test_family_member_created_event_writes_audit_via_handler(db):
    ws = await make_workspace(db)

    event = FamilyMemberCreatedEvent(
        aggregate_id="mem-1",
        aggregate_type="family_member",
        workspace_id=ws.id,
        member_id="mem-1",
        member_key="david",
        member_name="David Roberto",
        actor_user_id=ws.owner_id,
    )
    await dispatch_sync(event, {"db": db})
    await db.commit()

    entry = (await db.execute(select(AuditLog).where(AuditLog.workspace_id == ws.id))).scalar_one()
    assert entry.action == "family_member.created"
    assert entry.resource_type == "family_member"
    assert entry.resource_id == "mem-1"
    assert entry.actor_user_id == ws.owner_id
    assert entry.details == {"member_key": "david"}
    # nome completo NÃO deve ir para audit details (ADR-110 §PII)
    assert "David Roberto" not in str(entry.details)


@pytest.mark.asyncio
async def test_handler_without_db_raises_keyerror(db):
    event = AuditLogEvent(action="test.event", resource_type="test")
    with pytest.raises(KeyError):
        await dispatch_sync(event)


@pytest.mark.asyncio
async def test_rollback_discards_audit_on_use_case_failure(db):
    """Simula cenário: use case emite evento, depois levanta → rollback.

    Contrato: handler escreveu via ``db.add()`` + ``flush()``, mas commit é
    do caller. Se caller faz ``rollback``, a entrada some junto — audit
    nunca fica órfão de uma operação que falhou.
    """
    ws = await make_workspace(db)
    await db.commit()
    ws_id = ws.id

    event = AuditLogEvent(
        workspace_id=ws_id,
        action="test.event",
        resource_type="test",
    )
    await dispatch_sync(event, {"db": db})
    # Flush aconteceu mas commit não — rollback deve descartar.
    await db.rollback()

    # Nova transação implícita — lê direto do DB (o row flushed foi descartado).
    rows = (
        await db.execute(select(AuditLog).where(AuditLog.workspace_id == ws_id))
    ).scalars().all()
    assert rows == []
