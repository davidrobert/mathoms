"""Testes unitários do GoalRepository (com DB real).

Usam as fixtures ``db`` / ``setup_db`` de conftest.py (SQLite in-memory).
Cobrem:

- ``get_active_by_type`` retorna vigente ou None; cross-tenant isolation.
- ``list_by_workspace_and_type`` ordena por ``effective_from`` DESC.
- ``create_new_version`` fecha a vigente (se existir) antes de inserir
  a nova; o flush intermediário resolve o unique index parcial.
- ``get_by_id`` scoped ao workspace.
- ``goal_type`` inválido em qualquer método → ``ValueError``.
- Isolamento multi-tenant em todas as queries (R13).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workspace import Workspace
from backend.app.repositories.goal_repository import GoalRepository
from backend.tests.factories.builders import make_if_goal, make_workspace


@pytest_asyncio.fixture
async def two_workspaces(db: AsyncSession) -> tuple[Workspace, Workspace]:
    ws_a = await make_workspace(db, name="WS A")
    ws_b = await make_workspace(db, name="WS B")
    await db.commit()
    return ws_a, ws_b


# ---------------------------------------------------------------------------
# get_active_by_type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_active_by_type_returns_none_when_no_goal(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    repo = GoalRepository(db)

    result = await repo.get_active_by_type(ws_a.id, "INDEPENDENCIA_FINANCEIRA")

    assert result is None


@pytest.mark.asyncio
async def test_get_active_by_type_returns_current_version(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    goal = await make_if_goal(db, workspace=ws_a, renda_passiva_mensal_brl=25000)
    await db.commit()

    repo = GoalRepository(db)
    result = await repo.get_active_by_type(ws_a.id, "INDEPENDENCIA_FINANCEIRA")

    assert result is not None
    assert result.id == goal.id
    assert result.effective_to is None


@pytest.mark.asyncio
async def test_get_active_by_type_is_workspace_isolated(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces
    await make_if_goal(db, workspace=ws_a)
    await db.commit()

    repo = GoalRepository(db)
    # ws_b não tem goal — isolamento multi-tenant.
    assert await repo.get_active_by_type(ws_b.id, "INDEPENDENCIA_FINANCEIRA") is None


@pytest.mark.asyncio
async def test_get_active_by_type_invalid_type_raises(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    repo = GoalRepository(db)

    with pytest.raises(ValueError, match="inválido"):
        await repo.get_active_by_type(ws_a.id, "UNKNOWN_TYPE")


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_id_scoped_to_workspace(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces
    goal = await make_if_goal(db, workspace=ws_a)
    await db.commit()

    repo = GoalRepository(db)
    assert (await repo.get_by_id(ws_a.id, goal.id)) is not None
    # Cross-tenant: ws_b não deve enxergar.
    assert (await repo.get_by_id(ws_b.id, goal.id)) is None
    # Id inexistente.
    assert (await repo.get_by_id(ws_a.id, "nonexistent")) is None


# ---------------------------------------------------------------------------
# list_by_workspace_and_type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_by_workspace_and_type_empty(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    repo = GoalRepository(db)

    result = await repo.list_by_workspace_and_type(ws_a.id, "INDEPENDENCIA_FINANCEIRA")

    assert result == []


@pytest.mark.asyncio
async def test_list_by_workspace_and_type_orders_by_effective_from_desc(
    db: AsyncSession, two_workspaces
):
    ws_a, _ = two_workspaces

    # Cria 3 versões (vigente é a de effective_from=2026-03-01)
    older = await make_if_goal(db, workspace=ws_a, effective_from=date(2026, 1, 1))
    older.effective_to = date(2026, 1, 31)
    middle = await make_if_goal(db, workspace=ws_a, effective_from=date(2026, 2, 1))
    middle.effective_to = date(2026, 2, 28)
    newest = await make_if_goal(db, workspace=ws_a, effective_from=date(2026, 3, 1))
    # newest permanece vigente (effective_to = None)
    await db.commit()

    repo = GoalRepository(db)
    history = await repo.list_by_workspace_and_type(ws_a.id, "INDEPENDENCIA_FINANCEIRA")

    assert [g.id for g in history] == [newest.id, middle.id, older.id]


@pytest.mark.asyncio
async def test_list_by_workspace_and_type_is_tenant_isolated(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces
    await make_if_goal(db, workspace=ws_a)
    await make_if_goal(db, workspace=ws_b)
    await db.commit()

    repo = GoalRepository(db)
    a_list = await repo.list_by_workspace_and_type(ws_a.id, "INDEPENDENCIA_FINANCEIRA")
    b_list = await repo.list_by_workspace_and_type(ws_b.id, "INDEPENDENCIA_FINANCEIRA")

    assert len(a_list) == 1
    assert len(b_list) == 1
    assert a_list[0].workspace_id == ws_a.id
    assert b_list[0].workspace_id == ws_b.id


# ---------------------------------------------------------------------------
# create_new_version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_new_version_inserts_when_no_prior(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    repo = GoalRepository(db)

    new_goal = await repo.create_new_version(
        ws_a.id,
        "APORTE_MENSAL",
        params_json={"inputs": {"meta_aporte_mensal_brl": 5000}, "meta_version": 1},
        derived_json={"aporte_anual_brl": 60000, "distribuicao_pct": {}},
        created_by=None,
        notes="primeiro aporte",
    )
    await db.commit()

    assert new_goal.id is not None
    assert new_goal.type == "APORTE_MENSAL"
    assert new_goal.effective_from == date.today()
    assert new_goal.effective_to is None
    assert new_goal.notes == "primeiro aporte"


@pytest.mark.asyncio
async def test_create_new_version_closes_prior_active(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    prior = await make_if_goal(db, workspace=ws_a, renda_passiva_mensal_brl=20000)
    await db.commit()
    prior_id = prior.id

    repo = GoalRepository(db)
    eff_from = date.today() + timedelta(days=1)

    new_goal = await repo.create_new_version(
        ws_a.id,
        "INDEPENDENCIA_FINANCEIRA",
        params_json={
            "inputs": {
                "renda_passiva_mensal_brl": 25000,
                "trs_pct": 5.0,
                "retorno_real_anual_pct": 5.0,
                "horizonte_anos": 15,
                "taxa_retirada_conservadora_pct": 4.0,
            },
            "meta_version": 1,
        },
        derived_json={
            "if_meta_brl": 6000000.0,
            "aporte_necessario_mensal_brl": 20000.0,
            "if_meta_conservadora_brl": 7500000.0,
        },
        effective_from=eff_from,
    )
    await db.commit()

    # Re-carrega prior para verificar effective_to atualizado.
    prior_refreshed = await repo.get_by_id(ws_a.id, prior_id)

    assert prior_refreshed.effective_to == eff_from - timedelta(days=1)
    assert new_goal.effective_to is None
    # História ordenada DESC
    history = await repo.list_by_workspace_and_type(ws_a.id, "INDEPENDENCIA_FINANCEIRA")
    assert [g.id for g in history] == [new_goal.id, prior_id]


@pytest.mark.asyncio
async def test_create_new_version_invalid_type_raises(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    repo = GoalRepository(db)

    with pytest.raises(ValueError, match="inválido"):
        await repo.create_new_version(
            ws_a.id,
            "NOT_A_REAL_TYPE",
            params_json={"inputs": {}, "meta_version": 1},
            derived_json={},
        )


@pytest.mark.asyncio
async def test_create_new_version_is_tenant_isolated(db: AsyncSession, two_workspaces):
    """Goal em ws_a não fecha goal de ws_b (mesmo tipo)."""
    ws_a, ws_b = two_workspaces

    goal_b = await make_if_goal(db, workspace=ws_b)
    await db.commit()

    repo = GoalRepository(db)
    await repo.create_new_version(
        ws_a.id,
        "INDEPENDENCIA_FINANCEIRA",
        params_json={
            "inputs": {
                "renda_passiva_mensal_brl": 10000,
                "trs_pct": 5.0,
                "retorno_real_anual_pct": 5.0,
                "horizonte_anos": 10,
                "taxa_retirada_conservadora_pct": 4.0,
            },
            "meta_version": 1,
        },
        derived_json={
            "if_meta_brl": 2400000.0,
            "aporte_necessario_mensal_brl": 15000.0,
            "if_meta_conservadora_brl": 3000000.0,
        },
    )
    await db.commit()

    # Goal de ws_b deve continuar vigente.
    b_active = await repo.get_active_by_type(ws_b.id, "INDEPENDENCIA_FINANCEIRA")
    assert b_active is not None
    assert b_active.id == goal_b.id
    assert b_active.effective_to is None
