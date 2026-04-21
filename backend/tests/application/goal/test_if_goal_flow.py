"""Fluxo completo do goal IF: create → get → list."""

from __future__ import annotations

import pytest

from backend.app.application.base.errors import NotFoundError
from backend.app.application.goal import (
    create_if_goal_version,
    get_active_if_goal,
    list_if_goal_versions,
)
from backend.app.schemas.dto.goal import IFGoalInputs, IFGoalUpsertCommand
from backend.tests.fakes import FakeGoalRepository


def _inputs(**overrides) -> IFGoalInputs:
    base = dict(
        renda_passiva_mensal_brl=30_000,
        trs_pct=5.0,
        retorno_real_anual_pct=5.0,
        horizonte_anos=20,
    )
    base.update(overrides)
    return IFGoalInputs(**base)


@pytest.mark.asyncio
async def test_get_active_raises_not_found_when_no_version():
    repo = FakeGoalRepository()

    with pytest.raises(NotFoundError) as exc:
        await get_active_if_goal("ws-1", repo=repo)
    assert exc.value.code == "if_goal_not_configured"


@pytest.mark.asyncio
async def test_create_if_goal_version_persists_and_returns_enriched():
    repo = FakeGoalRepository()

    resp = await create_if_goal_version(
        IFGoalUpsertCommand(inputs=_inputs(), notes="revisão inicial"),
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
        patrimonio_atual_brl=720_000,
        created_by_name="David R.",
    )

    assert resp.created_by_name == "David R."
    assert resp.notes == "revisão inicial"
    # Derived recalculado com patrimônio atual (aporte_com_patrimonio preenchido).
    assert resp.derived.aporte_mensal_com_patrimonio_atual_brl is not None


@pytest.mark.asyncio
async def test_second_if_version_closes_previous():
    repo = FakeGoalRepository()
    await create_if_goal_version(
        IFGoalUpsertCommand(inputs=_inputs(renda_passiva_mensal_brl=30_000)),
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
    )
    await create_if_goal_version(
        IFGoalUpsertCommand(inputs=_inputs(renda_passiva_mensal_brl=50_000)),
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
    )

    # Só uma vigente (effective_to IS NULL) por workspace+type.
    active = await repo.get_active_by_type("ws-1", "INDEPENDENCIA_FINANCEIRA")
    assert active is not None
    assert active.params_json["inputs"]["renda_passiva_mensal_brl"] == 50_000


@pytest.mark.asyncio
async def test_get_active_returns_version_with_current_patrimonio():
    repo = FakeGoalRepository()
    await create_if_goal_version(
        IFGoalUpsertCommand(inputs=_inputs()),
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
    )

    resp = await get_active_if_goal(
        "ws-1",
        repo=repo,
        patrimonio_atual_brl=1_000_000,
        created_by_name="David R.",
    )

    assert resp.created_by_name == "David R."
    assert resp.derived.patrimonio_atual_utilizado_brl == 1_000_000.0


@pytest.mark.asyncio
async def test_list_if_goal_versions_maps_author_names():
    repo = FakeGoalRepository()
    await create_if_goal_version(
        IFGoalUpsertCommand(inputs=_inputs(renda_passiva_mensal_brl=30_000)),
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
    )
    await create_if_goal_version(
        IFGoalUpsertCommand(inputs=_inputs(renda_passiva_mensal_brl=50_000)),
        workspace_id="ws-1",
        created_by="user-2",
        repo=repo,
    )

    resp = await list_if_goal_versions(
        "ws-1",
        repo=repo,
        author_names={"user-1": "Ana", "user-2": "Bruno"},
    )

    assert resp.total == 2
    # Histórico ordenado mais recente primeiro.
    assert resp.goals[0].created_by_name == "Bruno"
    assert resp.goals[1].created_by_name == "Ana"
