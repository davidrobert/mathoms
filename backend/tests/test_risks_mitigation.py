"""Mitigation link/unlink do Risk aggregate (ADR-178 · Sprint A10.4).

Cobre os 6 cenários canônicos do link Decision↔Risk:
- Append idempotente
- Decision inválida (404)
- Cross-tenant Decision (validação)
- Unlink + idempotência
- Múltiplas mitigations
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ValidationError
from backend.app.application.decisions import create_decision
from backend.app.application.risks import (
    create_risk,
    link_mitigation,
    unlink_mitigation,
)
from backend.app.repositories.decision_repository import DecisionRepository
from backend.app.repositories.risk_repository import RiskRepository
from backend.app.schemas.dto.decision import DecisionCreateCommand
from backend.app.schemas.dto.risk import (
    RiskCreateCommand,
    RiskMitigationLinkCommand,
)
from backend.tests.factories.builders import make_workspace


@pytest_asyncio.fixture
async def setup(db: AsyncSession):
    ws = await make_workspace(db, name="WS Mitigation Test")
    await db.commit()
    return ws, RiskRepository(db), DecisionRepository(db)


@pytest_asyncio.fixture
async def two_workspaces(db: AsyncSession):
    ws_a = await make_workspace(db, name="WS A")
    ws_b = await make_workspace(db, name="WS B")
    await db.commit()
    return ws_a, ws_b, RiskRepository(db), DecisionRepository(db)


def _risk_cmd() -> RiskCreateCommand:
    return RiskCreateCommand(
        code="morte",
        name="Morte do provedor",
        rationale="Falecimento compromete renda — fictício.",
        impact_level="crítico",
    )


@pytest.mark.asyncio
async def test_link_mitigation_appends_decision_id(db, setup):
    ws, repo, decision_repo = setup
    risk = await create_risk(_risk_cmd(), workspace_id=ws.id, repo=repo)
    decision = await create_decision(
        DecisionCreateCommand(code="D01", title="Contratar seguro fictício"),
        workspace_id=ws.id,
        repo=decision_repo,
        actor="user:test",
    )
    await db.commit()

    resp = await link_mitigation(
        RiskMitigationLinkCommand(decision_id=decision.id),
        workspace_id=ws.id,
        risk_id=risk.id,
        risk_repo=repo,
        decision_repo=decision_repo,
    )
    await db.commit()
    assert resp.mitigations_decision_ids == [decision.id]


@pytest.mark.asyncio
async def test_link_mitigation_idempotent(db, setup):
    ws, repo, decision_repo = setup
    risk = await create_risk(_risk_cmd(), workspace_id=ws.id, repo=repo)
    decision = await create_decision(
        DecisionCreateCommand(code="D01", title="t"),
        workspace_id=ws.id,
        repo=decision_repo,
        actor="user:test",
    )
    await db.commit()

    cmd = RiskMitigationLinkCommand(decision_id=decision.id)
    await link_mitigation(
        cmd,
        workspace_id=ws.id,
        risk_id=risk.id,
        risk_repo=repo,
        decision_repo=decision_repo,
    )
    await db.commit()
    resp = await link_mitigation(
        cmd,
        workspace_id=ws.id,
        risk_id=risk.id,
        risk_repo=repo,
        decision_repo=decision_repo,
    )
    await db.commit()
    assert resp.mitigations_decision_ids == [decision.id]


@pytest.mark.asyncio
async def test_link_mitigation_invalid_decision_raises_validation(db, setup):
    ws, repo, decision_repo = setup
    risk = await create_risk(_risk_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    with pytest.raises(ValidationError) as exc:
        await link_mitigation(
            RiskMitigationLinkCommand(decision_id="00000000-0000-0000-0000-000000000000"),
            workspace_id=ws.id,
            risk_id=risk.id,
            risk_repo=repo,
            decision_repo=decision_repo,
        )
    assert exc.value.code == "invalid_decision"


@pytest.mark.asyncio
async def test_link_mitigation_cross_tenant_decision_blocked(db, two_workspaces):
    ws_a, ws_b, repo, decision_repo = two_workspaces
    risk = await create_risk(_risk_cmd(), workspace_id=ws_a.id, repo=repo)
    decision_b = await create_decision(
        DecisionCreateCommand(code="D01", title="Decision em B"),
        workspace_id=ws_b.id,
        repo=decision_repo,
        actor="user:test",
    )
    await db.commit()

    with pytest.raises(ValidationError):
        await link_mitigation(
            RiskMitigationLinkCommand(decision_id=decision_b.id),
            workspace_id=ws_a.id,
            risk_id=risk.id,
            risk_repo=repo,
            decision_repo=decision_repo,
        )


@pytest.mark.asyncio
async def test_unlink_mitigation_removes_decision_id(db, setup):
    ws, repo, decision_repo = setup
    risk = await create_risk(_risk_cmd(), workspace_id=ws.id, repo=repo)
    decision = await create_decision(
        DecisionCreateCommand(code="D01", title="t"),
        workspace_id=ws.id,
        repo=decision_repo,
        actor="user:test",
    )
    await db.commit()
    await link_mitigation(
        RiskMitigationLinkCommand(decision_id=decision.id),
        workspace_id=ws.id,
        risk_id=risk.id,
        risk_repo=repo,
        decision_repo=decision_repo,
    )
    await db.commit()

    resp = await unlink_mitigation(
        workspace_id=ws.id,
        risk_id=risk.id,
        decision_id=decision.id,
        risk_repo=repo,
    )
    await db.commit()
    assert resp.mitigations_decision_ids == []


@pytest.mark.asyncio
async def test_unlink_mitigation_idempotent(db, setup):
    ws, repo, _ = setup
    risk = await create_risk(_risk_cmd(), workspace_id=ws.id, repo=repo)
    await db.commit()

    resp = await unlink_mitigation(
        workspace_id=ws.id,
        risk_id=risk.id,
        decision_id="00000000-0000-0000-0000-000000000000",
        risk_repo=repo,
    )
    await db.commit()
    assert resp.mitigations_decision_ids == []


@pytest.mark.asyncio
async def test_link_multiple_mitigations(db, setup):
    ws, repo, decision_repo = setup
    risk = await create_risk(_risk_cmd(), workspace_id=ws.id, repo=repo)
    d1 = await create_decision(
        DecisionCreateCommand(code="D01", title="Seguro vida"),
        workspace_id=ws.id,
        repo=decision_repo,
        actor="user:test",
    )
    d2 = await create_decision(
        DecisionCreateCommand(code="D02", title="Reserva 12m"),
        workspace_id=ws.id,
        repo=decision_repo,
        actor="user:test",
    )
    await db.commit()

    await link_mitigation(
        RiskMitigationLinkCommand(decision_id=d1.id),
        workspace_id=ws.id,
        risk_id=risk.id,
        risk_repo=repo,
        decision_repo=decision_repo,
    )
    await db.commit()
    resp = await link_mitigation(
        RiskMitigationLinkCommand(decision_id=d2.id),
        workspace_id=ws.id,
        risk_id=risk.id,
        risk_repo=repo,
        decision_repo=decision_repo,
    )
    await db.commit()
    assert set(resp.mitigations_decision_ids) == {d1.id, d2.id}
