"""Testes do aggregate ``Risk`` — domínio (ADR-178 · Sprint A10.4).

Use cases + repo. DTO em ``test_risks_dto.py``; HTTP em
``test_risks_api.py`` para manter cada arquivo ≤500 linhas.

Valores fictícios em todos os testes — CLAUDE.md §Dados sensíveis.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
)
from backend.app.application.risks import (
    create_risk,
    delete_risk,
    get_risk,
    list_risks,
    update_risk,
)
from backend.app.repositories.decision_repository import DecisionRepository
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.schemas.dto.risk import (
    RiskCreateCommand,
    RiskUpdateCommand,
)
from backend.app.scripts.seed_workspace_risks import seed_default_risks
from backend.tests.factories.builders import make_workspace

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def setup(db: AsyncSession):
    ws = await make_workspace(db, name="WS Risk Test")
    await db.commit()
    return ws, RiskRepository(db), DecisionRepository(db)


@pytest_asyncio.fixture
async def two_workspaces(db: AsyncSession):
    ws_a = await make_workspace(db, name="WS Risk A")
    ws_b = await make_workspace(db, name="WS Risk B")
    await db.commit()
    return ws_a, ws_b, RiskRepository(db), DecisionRepository(db)


def _new_risk_cmd(**overrides) -> RiskCreateCommand:
    base = {
        "code": "morte",
        "name": "Morte do provedor",
        "rationale": "Falecimento compromete renda familiar — fictício.",
        "impact_level": "crítico",
    }
    base.update(overrides)
    return RiskCreateCommand(**base)


# ---------------------------------------------------------------------------
# Use case: create + get
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_risk_persists_with_defaults(db, setup):
    ws, repo, _ = setup
    resp = await create_risk(_new_risk_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    assert resp.code == "morte"
    assert resp.status == "Ativo"
    assert resp.probability is None
    assert resp.impact_level == "crítico"
    assert resp.impact_brl is None
    assert resp.mitigations_decision_ids == []


@pytest.mark.asyncio
async def test_create_risk_with_quantitative_impact(db, setup):
    ws, repo, _ = setup
    resp = await create_risk(
        _new_risk_cmd(impact_brl=Decimal("300000.00")),
        workspace_id=ws.id,
        repo=repo,
    )
    await db.commit()
    assert resp.impact_brl == Decimal("300000.00")


@pytest.mark.asyncio
async def test_create_duplicate_code_raises_conflict(db, setup):
    ws, repo, _ = setup
    await create_risk(_new_risk_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    with pytest.raises(ConflictError):
        await create_risk(_new_risk_cmd(name="Outro nome"), workspace_id=ws.id, repo=repo)


@pytest.mark.asyncio
async def test_get_risk_returns_persisted(db, setup):
    ws, repo, _ = setup
    created = await create_risk(_new_risk_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    fetched = await get_risk(ws.id, created.id, repo=repo)
    assert fetched.id == created.id
    assert fetched.name == "Morte do provedor"


@pytest.mark.asyncio
async def test_get_risk_404_for_nonexistent(db, setup):
    ws, repo, _ = setup
    with pytest.raises(NotFoundError):
        await get_risk(ws.id, "00000000-0000-0000-0000-000000000000", repo=repo)


# ---------------------------------------------------------------------------
# Use case: list + ordenação
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_risks_orders_by_impact_then_probability(db, setup):
    ws, repo, _ = setup
    await create_risk(
        _new_risk_cmd(code="desemprego", name="Desemprego", impact_level="médio"),
        workspace_id=ws.id,
        repo=repo,
    )
    await create_risk(
        _new_risk_cmd(code="morte", impact_level="crítico", probability="alta"),
        workspace_id=ws.id,
        repo=repo,
    )
    await create_risk(
        _new_risk_cmd(code="invalidez", name="Invalidez", impact_level="alto"),
        workspace_id=ws.id,
        repo=repo,
    )
    await create_risk(
        _new_risk_cmd(
            code="doenca_grave",
            name="Doença grave",
            impact_level="alto",
            probability="média",
        ),
        workspace_id=ws.id,
        repo=repo,
    )
    await db.commit()

    resp = await list_risks(ws.id, repo=repo)
    codes = [r.code for r in resp.risks]
    # crítico → alto (probability=média antes de None) → médio
    assert codes == ["morte", "doenca_grave", "invalidez", "desemprego"]
    assert resp.total == 4


@pytest.mark.asyncio
async def test_list_risks_empty_when_no_records(db, setup):
    ws, repo, _ = setup
    resp = await list_risks(ws.id, repo=repo)
    assert resp.total == 0
    assert resp.risks == []


# ---------------------------------------------------------------------------
# Use case: update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_risk_changes_probability(db, setup):
    ws, repo, _ = setup
    created = await create_risk(_new_risk_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    upd = await update_risk(
        RiskUpdateCommand(probability="alta", status="Mitigado"),
        workspace_id=ws.id,
        risk_id=created.id,
        repo=repo,
    )
    await db.commit()
    assert upd.probability == "alta"
    assert upd.status == "Mitigado"


@pytest.mark.asyncio
async def test_update_risk_quantifies_impact(db, setup):
    ws, repo, _ = setup
    created = await create_risk(_new_risk_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    upd = await update_risk(
        RiskUpdateCommand(impact_brl=Decimal("500000.00")),
        workspace_id=ws.id,
        risk_id=created.id,
        repo=repo,
    )
    await db.commit()
    assert upd.impact_brl == Decimal("500000.00")


@pytest.mark.asyncio
async def test_update_risk_404_for_nonexistent(db, setup):
    ws, repo, _ = setup
    with pytest.raises(NotFoundError):
        await update_risk(
            RiskUpdateCommand(status="Aceito"),
            workspace_id=ws.id,
            risk_id="00000000-0000-0000-0000-000000000000",
            repo=repo,
        )


# ---------------------------------------------------------------------------
# Use case: delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_risk_removes_record(db, setup):
    ws, repo, _ = setup
    created = await create_risk(_new_risk_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    await delete_risk(workspace_id=ws.id, risk_id=created.id, repo=repo)
    await db.commit()

    with pytest.raises(NotFoundError):
        await get_risk(ws.id, created.id, repo=repo)


@pytest.mark.asyncio
async def test_delete_risk_404_for_nonexistent(db, setup):
    ws, repo, _ = setup
    with pytest.raises(NotFoundError):
        await delete_risk(
            workspace_id=ws.id,
            risk_id="00000000-0000-0000-0000-000000000000",
            repo=repo,
        )


# ---------------------------------------------------------------------------
# Tenancy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_risk_isolated_per_workspace(db, two_workspaces):
    ws_a, ws_b, repo, _ = two_workspaces
    await create_risk(_new_risk_cmd(), workspace_id=ws_a.id, repo=repo)
    await db.commit()

    listed_a = await list_risks(ws_a.id, repo=repo)
    listed_b = await list_risks(ws_b.id, repo=repo)
    assert listed_a.total == 1
    assert listed_b.total == 0


@pytest.mark.asyncio
async def test_get_risk_cross_tenant_404(db, two_workspaces):
    ws_a, ws_b, repo, _ = two_workspaces
    created = await create_risk(_new_risk_cmd(), workspace_id=ws_a.id, repo=repo)
    await db.commit()

    with pytest.raises(NotFoundError):
        await get_risk(ws_b.id, created.id, repo=repo)


@pytest.mark.asyncio
async def test_same_code_in_two_workspaces_allowed(db, two_workspaces):
    ws_a, ws_b, repo, _ = two_workspaces
    await create_risk(_new_risk_cmd(), workspace_id=ws_a.id, repo=repo)
    await create_risk(_new_risk_cmd(), workspace_id=ws_b.id, repo=repo)
    await db.commit()
    # Não deve levantar — UNIQUE é (workspace_id, code).


# ---------------------------------------------------------------------------
# Seed Cerbasi
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_default_risks_creates_5_canonical_codes(db):
    ws = await make_workspace(db, name="WS Seeded")
    await db.commit()

    risks = await seed_default_risks(ws.id, db)
    await db.commit()

    expected_codes = {"morte", "invalidez", "doenca_grave", "desemprego", "longevidade"}
    assert {r.code for r in risks} == expected_codes
    assert len(risks) == 5


@pytest.mark.asyncio
async def test_seed_default_risks_initial_state(db):
    ws = await make_workspace(db, name="WS Seeded 2")
    await db.commit()

    risks = await seed_default_risks(ws.id, db)
    await db.commit()
    for r in risks:
        assert r.status == "Ativo"
        assert r.probability is None
        assert r.impact_brl_cents is None
        assert r.mitigations_decision_ids == []
        assert len(r.rationale) >= 10
