"""Integration — CreateFamilyMember emite evento que grava audit (A6e.events slice 2).

Valida o path completo: router → use case → dispatch_sync → handler → AuditLog.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.models.audit_log import AuditLog


@pytest.mark.asyncio
async def test_create_family_member_via_api_writes_audit_entry(auth_client, db):
    resp = await auth_client.post(
        f"/api/workspaces/{auth_client.ws_id}/config/members",
        json={
            "full_name": "David Roberto",
            "short_name": "David",
            "role": "titular",
        },
    )
    assert resp.status_code == 201
    member_id = resp.json()["id"]

    rows = (
        (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.workspace_id == auth_client.ws_id,
                    AuditLog.action == "family_member.created",
                )
            )
        )
        .scalars()
        .all()
    )

    assert len(rows) == 1
    entry = rows[0]
    assert entry.resource_type == "family_member"
    assert entry.resource_id == member_id
    assert entry.actor_user_id is not None  # veio do get_current_user
    assert entry.details == {"member_key": "david_roberto"}


@pytest.mark.asyncio
async def test_create_family_member_with_fake_db_stays_side_effect_free():
    """Contrato de compat: chamadas com ``db=None`` (testes puros com fakes)
    NÃO emitem evento. Previne regressão em ``test_create_family_member.py``.

    Adiciona um spy handler **sem limpar** os reais — spy registrado por
    último só dispara se alguém efetivamente emitir o evento.
    """
    from backend.app.application.family_member import create_family_member
    from backend.app.events import register_handler
    from backend.app.events.domain import FamilyMemberCreatedEvent
    from backend.app.events.registry import _HANDLERS
    from backend.app.schemas.dto.family_member import FamilyMemberCreateCommand
    from backend.tests.fakes import FakeFamilyMemberRepository, FakeVault

    called: list[str] = []

    @register_handler(FamilyMemberCreatedEvent)
    async def spy(event, deps):
        called.append(event.member_id)

    try:
        repo = FakeFamilyMemberRepository()
        vault = FakeVault()
        await create_family_member(
            FamilyMemberCreateCommand(full_name="Alice", short_name="A", role="titular"),
            workspace_id="ws-1",
            repo=repo,
            vault=vault,
            db=None,
        )
        assert called == []
    finally:
        # Remove apenas o spy — preserva handlers reais.
        _HANDLERS[FamilyMemberCreatedEvent] = [
            h for h in _HANDLERS.get(FamilyMemberCreatedEvent, ()) if h is not spy
        ]
