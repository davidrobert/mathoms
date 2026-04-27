"""Testes dos use cases do aggregate Decision (ADR-136).

Cobrem felicidade + erros de domínio (NotFound, Conflict, Validation).
Cada comando deve emitir um DecisionEvent append-only.

Valores fictícios em todos os testes (R$1.000, R$50.000) — nunca copiar
do `decisions.md` original (CLAUDE.md §Dados sensíveis).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.application.decisions import (
    create_decision,
    get_decision,
    list_decisions,
    mark_decision_executed,
    supersede_decision,
    update_decision,
)
from backend.app.repositories.decision_repository import DecisionRepository
from backend.app.schemas.dto.decision import (
    DecisionCreateCommand,
    DecisionExecuteCommand,
    DecisionSupersedeCommand,
    DecisionUpdateCommand,
)
from backend.tests.factories.builders import make_workspace


@pytest_asyncio.fixture
async def setup(db: AsyncSession):
    ws = await make_workspace(db, name="WS Test")
    await db.commit()
    return ws, DecisionRepository(db)


@pytest.mark.asyncio
async def test_create_decision_persists_and_emits_event(db, setup):
    ws, repo = setup

    cmd = DecisionCreateCommand(
        code="D01",
        title="Decisão fictícia",
        rationale="contexto fictício",
        amount_brl=Decimal("1000.00"),
    )
    resp = await create_decision(
        cmd, workspace_id=ws.id, repo=repo, actor="user:alice"
    )
    await db.commit()

    assert resp.code == "D01"
    assert resp.amount_brl == Decimal("1000.00")
    assert resp.status == "Pendente"

    events = await repo.list_events(resp.id)
    assert len(events) == 1
    assert events[0].event_type == "Created"
    assert events[0].actor == "user:alice"


@pytest.mark.asyncio
async def test_create_duplicate_code_raises_conflict(db, setup):
    ws, repo = setup

    cmd = DecisionCreateCommand(code="D01", title="Primeira")
    await create_decision(cmd, workspace_id=ws.id, repo=repo, actor="u")
    await db.commit()

    with pytest.raises(ConflictError):
        await create_decision(
            DecisionCreateCommand(code="D01", title="Outra"),
            workspace_id=ws.id,
            repo=repo,
            actor="u",
        )


@pytest.mark.asyncio
async def test_get_decision_404_for_nonexistent(db, setup):
    ws, repo = setup
    with pytest.raises(NotFoundError):
        await get_decision(ws.id, "00000000-0000-0000-0000-000000000000", repo=repo)


@pytest.mark.asyncio
async def test_list_decisions_ordered_by_code(db, setup):
    ws, repo = setup
    await create_decision(
        DecisionCreateCommand(code="D03", title="C"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    await create_decision(
        DecisionCreateCommand(code="D01", title="A"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    await db.commit()

    resp = await list_decisions(ws.id, repo=repo)
    assert resp.total == 2
    assert [d.code for d in resp.decisions] == ["D01", "D03"]


@pytest.mark.asyncio
async def test_update_decision_emits_diff_event(db, setup):
    ws, repo = setup
    created = await create_decision(
        DecisionCreateCommand(code="D01", title="Original"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    await db.commit()

    upd = await update_decision(
        DecisionUpdateCommand(title="Atualizado", amount_brl=Decimal("50000.00")),
        workspace_id=ws.id,
        decision_id=created.id,
        repo=repo,
        actor="user:bob",
    )
    await db.commit()

    assert upd.title == "Atualizado"
    assert upd.amount_brl == Decimal("50000.00")

    events = await repo.list_events(created.id)
    update_events = [e for e in events if e.event_type == "Updated"]
    assert len(update_events) == 1
    diff = update_events[0].payload["diff"]
    assert diff["title"] == "Atualizado"
    assert diff["amount_brl_cents"] == 5_000_000


@pytest.mark.asyncio
async def test_update_decision_no_changes_no_event(db, setup):
    ws, repo = setup
    created = await create_decision(
        DecisionCreateCommand(code="D01", title="Original"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    await db.commit()

    await update_decision(
        DecisionUpdateCommand(),
        workspace_id=ws.id,
        decision_id=created.id,
        repo=repo,
        actor="u",
    )
    await db.commit()

    events = await repo.list_events(created.id)
    assert [e.event_type for e in events] == ["Created"]


@pytest.mark.asyncio
async def test_mark_executed_transitions_status(db, setup):
    ws, repo = setup
    created = await create_decision(
        DecisionCreateCommand(code="D01", title="Quitar dívida fictícia"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    await db.commit()

    resp = await mark_decision_executed(
        DecisionExecuteCommand(note="quitado"),
        workspace_id=ws.id,
        decision_id=created.id,
        repo=repo,
        actor="user:alice",
    )
    await db.commit()

    assert resp.status == "Executado"
    assert resp.executed_at is not None

    events = await repo.list_events(created.id)
    assert any(e.event_type == "Executed" for e in events)


@pytest.mark.asyncio
async def test_mark_executed_rejects_already_executed(db, setup):
    ws, repo = setup
    created = await create_decision(
        DecisionCreateCommand(code="D01", title="t"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    await db.commit()
    await mark_decision_executed(
        DecisionExecuteCommand(),
        workspace_id=ws.id,
        decision_id=created.id,
        repo=repo,
        actor="u",
    )
    await db.commit()

    with pytest.raises(ValidationError) as exc:
        await mark_decision_executed(
            DecisionExecuteCommand(),
            workspace_id=ws.id,
            decision_id=created.id,
            repo=repo,
            actor="u",
        )
    assert exc.value.code == "invalid_transition"


@pytest.mark.asyncio
async def test_supersede_old_marked_chain_set(db, setup):
    ws, repo = setup
    old = await create_decision(
        DecisionCreateCommand(code="D06", title="Meta antiga"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    new = await create_decision(
        DecisionCreateCommand(code="D15", title="Meta nova"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    await db.commit()

    resp = await supersede_decision(
        DecisionSupersedeCommand(superseded_by_id=new.id, note="TRS 4→5"),
        workspace_id=ws.id,
        old_decision_id=old.id,
        repo=repo,
        actor="user:alice",
    )
    await db.commit()

    assert resp.status == "Superseded"

    new_resp = await get_decision(ws.id, new.id, repo=repo)
    assert new_resp.supersedes_id == old.id

    old_events = await repo.list_events(old.id)
    new_events = await repo.list_events(new.id)
    assert any(e.event_type == "Superseded" for e in old_events)
    assert any(e.event_type == "Superseded" for e in new_events)


@pytest.mark.asyncio
async def test_supersede_self_rejected(db, setup):
    ws, repo = setup
    d = await create_decision(
        DecisionCreateCommand(code="D01", title="t"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    await db.commit()

    with pytest.raises(ValidationError) as exc:
        await supersede_decision(
            DecisionSupersedeCommand(superseded_by_id=d.id),
            workspace_id=ws.id,
            old_decision_id=d.id,
            repo=repo,
            actor="u",
        )
    assert exc.value.code == "self_supersede"


@pytest.mark.asyncio
async def test_supersede_already_superseded_rejected(db, setup):
    ws, repo = setup
    old = await create_decision(
        DecisionCreateCommand(code="D06", title="o"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    new = await create_decision(
        DecisionCreateCommand(code="D15", title="n"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    newer = await create_decision(
        DecisionCreateCommand(code="D20", title="nn"),
        workspace_id=ws.id,
        repo=repo,
        actor="u",
    )
    await db.commit()
    await supersede_decision(
        DecisionSupersedeCommand(superseded_by_id=new.id),
        workspace_id=ws.id,
        old_decision_id=old.id,
        repo=repo,
        actor="u",
    )
    await db.commit()

    with pytest.raises(ValidationError) as exc:
        await supersede_decision(
            DecisionSupersedeCommand(superseded_by_id=newer.id),
            workspace_id=ws.id,
            old_decision_id=old.id,
            repo=repo,
            actor="u",
        )
    assert exc.value.code == "already_superseded"
