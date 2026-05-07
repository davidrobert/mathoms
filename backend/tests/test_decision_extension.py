"""Specs ADR-179 — Decision schema extension (impact_1y/10y, horizon, priority)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.application.decisions.create_decision import create_decision
from backend.app.application.decisions.update_decision import update_decision
from backend.app.models.decision import (
    DEFAULT_DECISION_HORIZON,
    VALID_DECISION_HORIZONS,
    Decision,
)
from backend.app.repositories.decision_repository import DecisionRepository
from backend.app.schemas.dto.decision import (
    DecisionCreateCommand,
    DecisionUpdateCommand,
)
from backend.app.schemas.dto.decision.mapper import decision_to_response
from backend.app.scripts.backfill_decision_impact import _heuristic_impact_1y
from backend.tests import factories


async def _setup_repo(db) -> tuple[DecisionRepository, str]:
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    return DecisionRepository(db), ws.id


async def _seed_decision(repo: DecisionRepository, ws_id: str, code: str, **kwargs) -> str:
    """Cria Decision via use case e retorna o id."""
    cmd = DecisionCreateCommand(code=code, title=f"t {code}", rationale="m", **kwargs)
    resp = await create_decision(cmd, workspace_id=ws_id, repo=repo, actor="t")
    return resp.id


# -----------------------------------------------------------------
# Modelo + DTO básico
# -----------------------------------------------------------------


def test_default_horizon_constant_matches_valid_set():
    assert DEFAULT_DECISION_HORIZON in VALID_DECISION_HORIZONS
    assert DEFAULT_DECISION_HORIZON == "short_6_12m"


def test_valid_horizons_set_is_exact_three():
    assert VALID_DECISION_HORIZONS == frozenset({"short_6_12m", "medium_1_3y", "long_5y_plus"})


# -----------------------------------------------------------------
# DTO validation
# -----------------------------------------------------------------


def test_create_command_accepts_omitted_horizon_priority():
    cmd = DecisionCreateCommand(code="D01", title="X", rationale="motivo amplo")
    assert cmd.horizon is None
    assert cmd.priority is None
    assert cmd.impact_1y_brl is None
    assert cmd.impact_10y_brl is None


def test_create_command_rejects_invalid_horizon():
    with pytest.raises(ValueError, match="horizon inválido"):
        DecisionCreateCommand(code="D01", title="X", horizon="forever")


def test_update_command_rejects_invalid_horizon():
    with pytest.raises(ValueError, match="horizon inválido"):
        DecisionUpdateCommand(horizon="forever")


def test_create_command_rejects_priority_out_of_range():
    with pytest.raises(ValueError):
        DecisionCreateCommand(code="D01", title="X", priority=0)
    with pytest.raises(ValueError):
        DecisionCreateCommand(code="D01", title="X", priority=100)


# -----------------------------------------------------------------
# Use case create + update
# -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_uses_default_horizon_when_omitted(db):
    repo, ws_id = await _setup_repo(db)
    cmd = DecisionCreateCommand(code="D01", title="Minha decisão", rationale="m")
    resp = await create_decision(cmd, workspace_id=ws_id, repo=repo, actor="t")
    await db.commit()
    assert resp.horizon == DEFAULT_DECISION_HORIZON
    assert resp.priority is None
    assert resp.impact_1y_brl is None
    assert resp.impact_10y_brl is None


@pytest.mark.asyncio
async def test_create_round_trips_all_four_fields(db):
    repo, ws_id = await _setup_repo(db)
    cmd = DecisionCreateCommand(
        code="D02",
        title="Quitar imóvel",
        rationale="liberar fluxo",
        impact_1y_brl=Decimal("36000.00"),
        impact_10y_brl=Decimal("420000.00"),
        horizon="medium_1_3y",
        priority=3,
    )
    resp = await create_decision(cmd, workspace_id=ws_id, repo=repo, actor="t")
    await db.commit()
    assert resp.impact_1y_brl == Decimal("36000.00")
    assert resp.impact_10y_brl == Decimal("420000.00")
    assert resp.horizon == "medium_1_3y"
    assert resp.priority == 3


async def _patch(repo, ws_id, decision_id, db, **fields):
    cmd = DecisionUpdateCommand(**fields)
    resp = await update_decision(
        cmd, workspace_id=ws_id, decision_id=decision_id, repo=repo, actor="t"
    )
    await db.commit()
    return resp


@pytest.mark.asyncio
async def test_update_patches_each_extension_field_individually(db):
    repo, ws_id = await _setup_repo(db)
    decision_id = await _seed_decision(repo, ws_id, "D03")
    await db.commit()

    r1 = await _patch(repo, ws_id, decision_id, db, impact_1y_brl=Decimal("12000.00"))
    assert r1.impact_1y_brl == Decimal("12000.00")
    assert r1.horizon == DEFAULT_DECISION_HORIZON

    r2 = await _patch(repo, ws_id, decision_id, db, horizon="long_5y_plus")
    assert r2.horizon == "long_5y_plus"
    assert r2.impact_1y_brl == Decimal("12000.00")

    r3 = await _patch(repo, ws_id, decision_id, db, priority=7)
    assert r3.priority == 7


# -----------------------------------------------------------------
# Mapper
# -----------------------------------------------------------------


def test_mapper_converts_impact_cents_to_decimal():
    decision = Decision(
        id="00000000-0000-0000-0000-000000000001",
        workspace_id="ws-1",
        code="D04",
        title="t",
        status="Pendente",
        horizon="short_6_12m",
        impact_1y_brl_cents=3_600_000,
        impact_10y_brl_cents=42_000_000,
        priority=5,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    resp = decision_to_response(decision)
    assert resp.impact_1y_brl == Decimal("36000.00")
    assert resp.impact_10y_brl == Decimal("420000.00")
    assert resp.horizon == "short_6_12m"
    assert resp.priority == 5


# -----------------------------------------------------------------
# Backfill heuristic (ADR-179 §migrator)
# -----------------------------------------------------------------


def _build_decision(**overrides) -> Decision:
    defaults = {
        "id": "x" * 36,
        "workspace_id": "ws-1",
        "code": "D01",
        "title": "t",
        "status": "Pendente",
        "horizon": "short_6_12m",
        "amount_brl_cents": None,
        "target_field": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return Decision(**defaults)


def test_heuristic_aporte_mensal_times_twelve():
    d = _build_decision(
        amount_brl_cents=300_000,
        target_field="goal.aporte.meta_aporte_mensal_brl",
        status="Decidido",
    )
    assert _heuristic_impact_1y(d) == 3_600_000


def test_heuristic_dolar_aporte_times_twelve():
    d = _build_decision(
        amount_brl_cents=200_000,
        target_field="goal.dolar.aporte_mensal_brl",
        status="Pendente",  # qualquer status — heurística vê target
    )
    assert _heuristic_impact_1y(d) == 2_400_000


def test_heuristic_valor_unico_decidido():
    d = _build_decision(
        amount_brl_cents=12_000_000,
        target_field=None,
        status="Decidido",
    )
    assert _heuristic_impact_1y(d) == 12_000_000


def test_heuristic_skips_pendente_without_target():
    d = _build_decision(
        amount_brl_cents=12_000_000,
        target_field=None,
        status="Pendente",
    )
    assert _heuristic_impact_1y(d) is None


def test_heuristic_skips_when_amount_is_null():
    d = _build_decision(
        amount_brl_cents=None,
        target_field=None,
        status="Decidido",
    )
    assert _heuristic_impact_1y(d) is None


# -----------------------------------------------------------------
# Ordenação (gate empírico para A10.5)
# -----------------------------------------------------------------


def _query_ordered_for_s10(ws_id: str):
    """Query da projeção S10: priority NULLS LAST, então impact_1y DESC NULLS LAST."""
    return (
        select(Decision)
        .where(Decision.workspace_id == ws_id)
        .order_by(
            Decision.priority.is_(None),
            Decision.priority.asc(),
            Decision.impact_1y_brl_cents.is_(None),
            Decision.impact_1y_brl_cents.desc(),
        )
    )


@pytest.mark.asyncio
async def test_ordering_by_priority_then_impact_desc(db):
    """ADR-179 §3 — gate para A10.5 (charts_narrator card S10)."""
    repo, ws_id = await _setup_repo(db)
    await _seed_decision(repo, ws_id, "D01", priority=1, impact_1y_brl=Decimal("100"))
    await _seed_decision(repo, ws_id, "D02", priority=5, impact_1y_brl=Decimal("200"))
    await _seed_decision(repo, ws_id, "D03", impact_1y_brl=Decimal("99999"))
    await _seed_decision(repo, ws_id, "D04", impact_1y_brl=Decimal("50"))
    await db.commit()

    rows = await db.execute(_query_ordered_for_s10(ws_id))
    codes = [d.code for d in rows.scalars().all()]
    assert codes == ["D01", "D02", "D03", "D04"]
