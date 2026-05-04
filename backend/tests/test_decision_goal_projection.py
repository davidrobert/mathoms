"""Testes da projeção Decision → Goal (ADR-162).

Cobertura:
- mark_executed com target_field cria nova Goal version (felicidade)
- target_field=None preserva legado (sem projection)
- target_field não-mapeado → ValidationError
- target_value não-parseável → ValidationError
- Goal vigente ausente → ValidationError
- Notes na Goal nova citam Decision.code
- DecisionEvent ``GoalProjected`` é emitido com goal_id
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ValidationError
from backend.app.application.decisions import create_decision, mark_decision_executed
from backend.app.models.decision import DecisionEvent
from backend.app.models.goal import Goal
from backend.app.repositories.decision_repository import DecisionRepository
from backend.app.repositories.goal_repository import GoalRepository
from backend.app.schemas.dto.decision import (
    DecisionCreateCommand,
    DecisionExecuteCommand,
)
from backend.tests.factories.builders import make_if_goal, make_workspace


@pytest_asyncio.fixture
async def setup(db: AsyncSession):
    ws = await make_workspace(db, name="WS Projection")
    await db.commit()
    return ws, DecisionRepository(db)


@pytest.mark.asyncio
async def test_execute_with_target_field_creates_new_goal_version(db, setup):
    """Marcar Decision como Executada com target_field=goal.if.trs_pct
    cria nova Goal version com TRS atualizado e fecha a anterior."""
    ws, repo = setup
    initial = await make_if_goal(db, workspace=ws, trs_pct=4.5)
    await db.commit()

    decision_resp = await create_decision(
        DecisionCreateCommand(
            code="D01",
            title="Reduzir TRS para 4%",
            target_field="goal.if.trs_pct",
            target_value="4.0",
            target_value_type="pct",
        ),
        workspace_id=ws.id,
        repo=repo,
        actor="test-user",
    )
    await db.commit()

    await mark_decision_executed(
        DecisionExecuteCommand(),
        workspace_id=ws.id,
        decision_id=decision_resp.id,
        repo=repo,
        actor="test-user",
        db=db,
    )
    await db.commit()

    goal_repo = GoalRepository(db)
    current = await goal_repo.get_active_by_type(ws.id, "INDEPENDENCIA_FINANCEIRA")
    assert current is not None
    assert current.id != initial.id  # nova versão
    assert current.params_json["inputs"]["trs_pct"] == 4.0
    assert "D01" in (current.notes or "")


@pytest.mark.asyncio
async def test_execute_without_target_field_skips_projection(db, setup):
    """Decision sem target_field continua terminal (legado)."""
    ws, repo = setup
    initial = await make_if_goal(db, workspace=ws, trs_pct=4.5)
    await db.commit()

    decision_resp = await create_decision(
        DecisionCreateCommand(code="D02", title="Conversar com consultor"),
        workspace_id=ws.id,
        repo=repo,
        actor="test-user",
    )
    await db.commit()

    await mark_decision_executed(
        DecisionExecuteCommand(),
        workspace_id=ws.id,
        decision_id=decision_resp.id,
        repo=repo,
        actor="test-user",
        db=db,
    )
    await db.commit()

    goal_repo = GoalRepository(db)
    current = await goal_repo.get_active_by_type(ws.id, "INDEPENDENCIA_FINANCEIRA")
    assert current is not None
    assert current.id == initial.id  # nada mudou


@pytest.mark.asyncio
async def test_execute_with_unregistered_target_field_raises(db, setup):
    ws, repo = setup
    decision_resp = await create_decision(
        DecisionCreateCommand(
            code="D03",
            title="Patch absurdo",
            target_field="goal.x.does_not_exist",
            target_value="10.0",
            target_value_type="pct",
        ),
        workspace_id=ws.id,
        repo=repo,
        actor="test-user",
    )
    await db.commit()

    with pytest.raises(ValidationError) as exc:
        await mark_decision_executed(
            DecisionExecuteCommand(),
            workspace_id=ws.id,
            decision_id=decision_resp.id,
            repo=repo,
            actor="test-user",
            db=db,
        )
    assert "projection_not_registered" in exc.value.code


@pytest.mark.asyncio
async def test_execute_with_unparseable_target_value_raises(db, setup):
    ws, repo = setup
    await make_if_goal(db, workspace=ws)
    decision_resp = await create_decision(
        DecisionCreateCommand(
            code="D04",
            title="TRS inválida",
            target_field="goal.if.trs_pct",
            target_value="not_a_number",
            target_value_type="pct",
        ),
        workspace_id=ws.id,
        repo=repo,
        actor="test-user",
    )
    await db.commit()

    with pytest.raises(ValidationError) as exc:
        await mark_decision_executed(
            DecisionExecuteCommand(),
            workspace_id=ws.id,
            decision_id=decision_resp.id,
            repo=repo,
            actor="test-user",
            db=db,
        )
    assert "parse_error" in exc.value.code


@pytest.mark.asyncio
async def test_execute_emits_goal_projected_event(db, setup):
    ws, repo = setup
    await make_if_goal(db, workspace=ws, trs_pct=5.0)
    await db.commit()

    decision_resp = await create_decision(
        DecisionCreateCommand(
            code="D05",
            title="Reduzir TRS",
            target_field="goal.if.trs_pct",
            target_value="4.0",
            target_value_type="pct",
        ),
        workspace_id=ws.id,
        repo=repo,
        actor="test-user",
    )
    await db.commit()

    await mark_decision_executed(
        DecisionExecuteCommand(),
        workspace_id=ws.id,
        decision_id=decision_resp.id,
        repo=repo,
        actor="test-user",
        db=db,
    )
    await db.commit()

    rows = (
        (
            await db.execute(
                select(DecisionEvent).where(
                    DecisionEvent.decision_id == decision_resp.id,
                    DecisionEvent.event_type == "GoalProjected",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    payload = rows[0].payload
    assert payload["target_field"] == "goal.if.trs_pct"
    assert payload["target_value"] == "4.0"
    assert "goal_id" in payload


@pytest.mark.asyncio
async def test_execute_without_active_goal_raises(db, setup):
    """Decision com target_field para Goal type sem versão vigente → erro."""
    ws, repo = setup
    # Sem Goal IF criado
    decision_resp = await create_decision(
        DecisionCreateCommand(
            code="D06",
            title="Patch sem goal base",
            target_field="goal.if.trs_pct",
            target_value="4.0",
            target_value_type="pct",
        ),
        workspace_id=ws.id,
        repo=repo,
        actor="test-user",
    )
    await db.commit()

    with pytest.raises(ValidationError) as exc:
        await mark_decision_executed(
            DecisionExecuteCommand(),
            workspace_id=ws.id,
            decision_id=decision_resp.id,
            repo=repo,
            actor="test-user",
            db=db,
        )
    assert "goal_not_found" in exc.value.code
