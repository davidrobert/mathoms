"""Testes do DecisionRepository (DB SQLite in-memory).

Cobrem:
- get_by_id / get_by_code / list_by_workspace (com isolamento cross-tenant)
- add(decision) flush + add_event(event) append-only
- list_events ordena por occurred_at ASC
- UNIQUE (workspace_id, code) — caller garante via use case; aqui só
  validamos que repo escreve sem reescrever.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.decision import Decision, DecisionEvent
from backend.app.models.workspace import Workspace
from backend.app.repositories.decision_repository import DecisionRepository
from backend.tests.factories.builders import make_workspace


@pytest_asyncio.fixture
async def two_workspaces(db: AsyncSession) -> tuple[Workspace, Workspace]:
    ws_a = await make_workspace(db, name="WS A")
    ws_b = await make_workspace(db, name="WS B")
    await db.commit()
    return ws_a, ws_b


def _new_decision(workspace_id: str, *, code: str = "D01") -> Decision:
    return Decision(
        workspace_id=workspace_id,
        code=code,
        title=f"Decisão fictícia {code}",
        rationale=None,
        amount_brl_cents=100_000,  # R$1.000,00 — fictício
        status="Pendente",
    )


@pytest.mark.asyncio
async def test_add_persists_decision(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    repo = DecisionRepository(db)

    saved = await repo.add(_new_decision(ws_a.id))
    await db.commit()

    fetched = await repo.get_by_id(ws_a.id, saved.id)
    assert fetched is not None
    assert fetched.code == "D01"
    assert fetched.amount_brl_cents == 100_000


@pytest.mark.asyncio
async def test_get_by_code_scoped_to_workspace(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces
    repo = DecisionRepository(db)
    await repo.add(_new_decision(ws_a.id, code="D01"))
    await db.commit()

    assert await repo.get_by_code(ws_a.id, "D01") is not None
    # mesmo code, tenant diferente → None (multi-tenant isolation)
    assert await repo.get_by_code(ws_b.id, "D01") is None


@pytest.mark.asyncio
async def test_list_by_workspace_ordered_by_code(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    repo = DecisionRepository(db)
    await repo.add(_new_decision(ws_a.id, code="D03"))
    await repo.add(_new_decision(ws_a.id, code="D01"))
    await repo.add(_new_decision(ws_a.id, code="D02"))
    await db.commit()

    rows = await repo.list_by_workspace(ws_a.id)
    assert [r.code for r in rows] == ["D01", "D02", "D03"]


@pytest.mark.asyncio
async def test_unique_constraint_workspace_code(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    repo = DecisionRepository(db)
    await repo.add(_new_decision(ws_a.id, code="D01"))
    await db.commit()

    with pytest.raises(IntegrityError):
        await repo.add(_new_decision(ws_a.id, code="D01"))
        await db.commit()


@pytest.mark.asyncio
async def test_add_event_appends_log(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    repo = DecisionRepository(db)
    decision = await repo.add(_new_decision(ws_a.id))
    await db.commit()

    event = DecisionEvent(
        decision_id=decision.id,
        event_type="Created",
        actor="system:test",
        payload={"code": "D01"},
    )
    await repo.add_event(event)
    await db.commit()

    events = await repo.list_events(decision.id)
    assert len(events) == 1
    assert events[0].event_type == "Created"
    assert events[0].payload == {"code": "D01"}
