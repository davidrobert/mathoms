"""Fluxo tipado: create → get → list para aportes/dólar/alocação."""

from __future__ import annotations

import pytest

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.goal import (
    create_typed_goal_version,
    get_active_typed_goal,
    list_typed_goal_versions,
)
from backend.app.schemas.dto.goal import (
    AlocacaoGoalInputs,
    AporteGoalInputs,
    DolarGoalInputs,
)
from backend.tests.fakes import FakeGoalRepository


@pytest.mark.asyncio
async def test_create_aporte_goal_persists_and_returns():
    repo = FakeGoalRepository()

    resp = await create_typed_goal_version(
        "APORTE_MENSAL",
        AporteGoalInputs(meta_aporte_mensal_brl=8_000, distribuicao={"acoes": 8_000}),
        notes="start",
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
    )

    assert resp.type == "APORTE_MENSAL"


@pytest.mark.asyncio
async def test_create_dolar_goal_uses_dolar_compute():
    repo = FakeGoalRepository()

    resp = await create_typed_goal_version(
        "DOLARIZACAO",
        DolarGoalInputs(meta_usd=50_000, aporte_mensal_brl=3_000),
        notes=None,
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
    )

    assert resp.type == "DOLARIZACAO"


@pytest.mark.asyncio
async def test_create_alocacao_goal_uses_alocacao_compute():
    repo = FakeGoalRepository()

    resp = await create_typed_goal_version(
        "ALOCACAO_ALVO",
        AlocacaoGoalInputs(
            renda_fixa_pct=50, acoes_pct=30, imoveis_reits_pct=15, liquidez_usd_pct=5
        ),
        notes=None,
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
    )

    assert resp.type == "ALOCACAO_ALVO"


@pytest.mark.asyncio
async def test_create_with_mismatched_inputs_raises_validation_error():
    repo = FakeGoalRepository()

    with pytest.raises(ValidationError):
        await create_typed_goal_version(
            "APORTE_MENSAL",
            DolarGoalInputs(meta_usd=50_000, aporte_mensal_brl=3_000),
            notes=None,
            workspace_id="ws-1",
            created_by="user-1",
            repo=repo,
        )


@pytest.mark.asyncio
async def test_get_active_typed_raises_not_found_when_empty():
    repo = FakeGoalRepository()

    with pytest.raises(NotFoundError):
        await get_active_typed_goal("ws-1", "APORTE_MENSAL", repo=repo)


@pytest.mark.asyncio
async def test_get_active_typed_returns_persisted_goal():
    repo = FakeGoalRepository()
    await create_typed_goal_version(
        "APORTE_MENSAL",
        AporteGoalInputs(meta_aporte_mensal_brl=8_000, distribuicao={"acoes": 8_000}),
        notes=None,
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
    )

    resp = await get_active_typed_goal("ws-1", "APORTE_MENSAL", repo=repo, created_by_name="Ana")

    assert resp.type == "APORTE_MENSAL"
    assert resp.created_by_name == "Ana"


@pytest.mark.asyncio
async def test_list_typed_goal_versions_orders_desc_and_maps_authors():
    repo = FakeGoalRepository()
    await create_typed_goal_version(
        "APORTE_MENSAL",
        AporteGoalInputs(meta_aporte_mensal_brl=5_000, distribuicao={"acoes": 5_000}),
        notes=None,
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
    )
    await create_typed_goal_version(
        "APORTE_MENSAL",
        AporteGoalInputs(meta_aporte_mensal_brl=10_000, distribuicao={"acoes": 10_000}),
        notes=None,
        workspace_id="ws-1",
        created_by="user-2",
        repo=repo,
    )

    goals = await list_typed_goal_versions(
        "ws-1",
        "APORTE_MENSAL",
        repo=repo,
        author_names={"user-1": "Ana", "user-2": "Bruno"},
    )

    assert len(goals) == 2
    assert goals[0].created_by_name == "Bruno"  # mais recente
    assert goals[1].created_by_name == "Ana"


@pytest.mark.asyncio
async def test_get_active_isolates_by_workspace():
    repo = FakeGoalRepository()
    await create_typed_goal_version(
        "APORTE_MENSAL",
        AporteGoalInputs(meta_aporte_mensal_brl=8_000, distribuicao={"acoes": 8_000}),
        notes=None,
        workspace_id="ws-1",
        created_by="user-1",
        repo=repo,
    )

    with pytest.raises(NotFoundError):
        await get_active_typed_goal("ws-other", "APORTE_MENSAL", repo=repo)
