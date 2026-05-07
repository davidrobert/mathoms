"""Testes do `pipeline_adapter` — projeções A10.5 (ADR-178/179)."""

from __future__ import annotations

import pytest

from backend.app.models.decision import Decision
from backend.app.models.risk import Risk
from backend.app.services.pipeline_adapter import (
    _project_risks_bubble_async,
    _project_top5_decisions_async,
    build_goals_payload,
)
from backend.tests import factories


def _make_decision(workspace_id: str, **overrides) -> Decision:
    defaults = dict(
        workspace_id=workspace_id,
        code="D01",
        title="Decisão exemplo",
        rationale="rationale",
        amount_brl_cents=None,
        status="Pendente",
        horizon="short_6_12m",
        impact_1y_brl_cents=None,
        priority=None,
    )
    defaults.update(overrides)
    return Decision(**defaults)


def _make_risk(workspace_id: str, **overrides) -> Risk:
    defaults = dict(
        workspace_id=workspace_id,
        code="rk-1",
        name="Risco exemplo",
        rationale="rationale",
        probability=None,
        impact_level="médio",
        impact_brl_cents=None,
        status="Ativo",
        mitigations_decision_ids=[],
    )
    defaults.update(overrides)
    return Risk(**defaults)


# ════════════════════════════════════════════════════════════════════
# Shape do payload — chaves sempre presentes (lista vazia se DB vazio)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_payload_has_projection_keys_even_when_empty(db):
    """Workspace sem Decisions/Risks ainda recebe as duas chaves vazias."""
    ws = await factories.make_workspace(db)
    payload = await build_goals_payload(ws.id, db=db)
    assert payload["top5_decisoes_projection"] == []
    assert payload["risks_projection"] == []


_TOP5_ITEM_KEYS = {"title", "rationale", "impact_1y_brl_cents", "horizon", "status"}


@pytest.mark.asyncio
async def test_top5_projection_item_shape(db):
    ws = await factories.make_workspace(db)
    db.add(_make_decision(ws.id, code="D02", title="Aporte", impact_1y_brl_cents=24_000_000))
    await db.commit()
    items = (await build_goals_payload(ws.id, db=db))["top5_decisoes_projection"]
    assert len(items) == 1 and set(items[0].keys()) == _TOP5_ITEM_KEYS
    assert items[0]["title"] == "Aporte" and items[0]["impact_1y_brl_cents"] == 24_000_000


_RISK_ITEM_KEYS = {"name", "code", "probability", "impact_level", "impact_brl_cents"}


@pytest.mark.asyncio
async def test_risk_projection_item_shape(db):
    ws = await factories.make_workspace(db)
    db.add(
        _make_risk(ws.id, code="morte", name="Morte", impact_level="crítico", probability="alta")
    )
    await db.commit()
    items = (await build_goals_payload(ws.id, db=db))["risks_projection"]
    assert len(items) == 1 and set(items[0].keys()) == _RISK_ITEM_KEYS
    assert items[0]["impact_level"] == "crítico" and items[0]["probability"] == "alta"


# ════════════════════════════════════════════════════════════════════
# Ordenação Decision (priority NULLS LAST → impact_1y DESC NULLS LAST)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_top5_priority_takes_precedence_over_impact(db):
    """Priority manual do consultor > impact_1y_brl_cents."""
    ws = await factories.make_workspace(db)
    # D01: priority None + impact 10B; D02: priority 1 + impact 100k → D02 first.
    db.add(
        _make_decision(ws.id, code="D01", title="big-no-prio", impact_1y_brl_cents=10_000_000_000)
    )
    db.add(
        _make_decision(
            ws.id, code="D02", title="small-prio-1", priority=1, impact_1y_brl_cents=100_000
        )
    )
    await db.commit()
    items = await _project_top5_decisions_async(ws.id, db=db)
    assert [i["title"] for i in items] == ["small-prio-1", "big-no-prio"]


@pytest.mark.asyncio
async def test_top5_orders_by_impact_when_priority_is_null(db):
    ws = await factories.make_workspace(db)
    db.add(_make_decision(ws.id, code="D01", impact_1y_brl_cents=100_000))
    db.add(_make_decision(ws.id, code="D02", impact_1y_brl_cents=900_000))
    db.add(_make_decision(ws.id, code="D03", impact_1y_brl_cents=500_000))
    await db.commit()

    items = await _project_top5_decisions_async(ws.id, db=db)
    impacts = [i["impact_1y_brl_cents"] for i in items]
    assert impacts == sorted(impacts, reverse=True)


@pytest.mark.asyncio
async def test_top5_null_impact_goes_last(db):
    ws = await factories.make_workspace(db)
    db.add(_make_decision(ws.id, code="D01", impact_1y_brl_cents=None))
    db.add(_make_decision(ws.id, code="D02", impact_1y_brl_cents=500_000))
    await db.commit()

    items = await _project_top5_decisions_async(ws.id, db=db)
    # D02 com impacto numérico antes de D01 com impacto None.
    assert items[0]["impact_1y_brl_cents"] == 500_000
    assert items[1]["impact_1y_brl_cents"] is None


# ════════════════════════════════════════════════════════════════════
# Filtragem Decision (horizon, status)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_top5_filters_horizon_short(db):
    """Apenas horizon=short_6_12m entra no card S10."""
    ws = await factories.make_workspace(db)
    db.add(_make_decision(ws.id, code="D01", horizon="short_6_12m"))
    db.add(_make_decision(ws.id, code="D02", horizon="medium_1_3y"))
    db.add(_make_decision(ws.id, code="D03", horizon="long_5y_plus"))
    await db.commit()

    items = await _project_top5_decisions_async(ws.id, db=db)
    assert len(items) == 1
    assert items[0]["horizon"] == "short_6_12m"


@pytest.mark.asyncio
async def test_top5_filters_status_decidido_pendente(db):
    """Apenas Decisions ativas (Decidido/Pendente) — Executado/Descartado/Superseded fora."""
    ws = await factories.make_workspace(db)
    db.add(_make_decision(ws.id, code="D01", status="Pendente"))
    db.add(_make_decision(ws.id, code="D02", status="Decidido"))
    db.add(_make_decision(ws.id, code="D03", status="Executado"))
    db.add(_make_decision(ws.id, code="D04", status="Descartado"))
    db.add(_make_decision(ws.id, code="D05", status="Superseded"))
    await db.commit()

    items = await _project_top5_decisions_async(ws.id, db=db)
    statuses = {i["status"] for i in items}
    assert statuses == {"Pendente", "Decidido"}
    assert len(items) == 2


@pytest.mark.asyncio
async def test_top5_limit_is_five(db):
    ws = await factories.make_workspace(db)
    for i in range(8):
        db.add(_make_decision(ws.id, code=f"D{i:02d}", impact_1y_brl_cents=10**i))
    await db.commit()

    items = await _project_top5_decisions_async(ws.id, db=db)
    assert len(items) == 5


# ════════════════════════════════════════════════════════════════════
# Ordenação Risk (impact_level → probability)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_risks_order_by_impact_level_critico_first(db):
    ws = await factories.make_workspace(db)
    db.add(_make_risk(ws.id, code="rk-baixo", impact_level="baixo"))
    db.add(_make_risk(ws.id, code="rk-critico", impact_level="crítico"))
    db.add(_make_risk(ws.id, code="rk-medio", impact_level="médio"))
    db.add(_make_risk(ws.id, code="rk-alto", impact_level="alto"))
    await db.commit()

    items = await _project_risks_bubble_async(ws.id, db=db)
    levels = [i["impact_level"] for i in items]
    assert levels == ["crítico", "alto", "médio", "baixo"]


@pytest.mark.asyncio
async def test_risks_order_by_probability_when_impact_ties(db):
    ws = await factories.make_workspace(db)
    db.add(_make_risk(ws.id, code="rk-a", impact_level="alto", probability="baixa"))
    db.add(_make_risk(ws.id, code="rk-b", impact_level="alto", probability="alta"))
    db.add(_make_risk(ws.id, code="rk-c", impact_level="alto", probability="média"))
    await db.commit()

    items = await _project_risks_bubble_async(ws.id, db=db)
    probs = [i["probability"] for i in items]
    assert probs == ["alta", "média", "baixa"]


@pytest.mark.asyncio
async def test_risks_null_probability_goes_last(db):
    ws = await factories.make_workspace(db)
    db.add(_make_risk(ws.id, code="rk-a", impact_level="alto", probability=None))
    db.add(_make_risk(ws.id, code="rk-b", impact_level="alto", probability="alta"))
    await db.commit()

    items = await _project_risks_bubble_async(ws.id, db=db)
    assert items[0]["probability"] == "alta"
    assert items[1]["probability"] is None


@pytest.mark.asyncio
async def test_risks_limit_is_eight(db):
    ws = await factories.make_workspace(db)
    for i in range(12):
        db.add(_make_risk(ws.id, code=f"rk-{i:02d}", impact_level="médio"))
    await db.commit()

    items = await _project_risks_bubble_async(ws.id, db=db)
    assert len(items) == 8


# ════════════════════════════════════════════════════════════════════
# Isolamento cross-workspace (R13/R14 — ADR-101)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_projections_isolated_between_workspaces(db):
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    db.add(_make_decision(ws_a.id, code="D01", title="A"))
    db.add(_make_risk(ws_a.id, code="rk-a", name="RA"))
    await db.commit()

    payload_a = await build_goals_payload(ws_a.id, db=db)
    payload_b = await build_goals_payload(ws_b.id, db=db)

    assert len(payload_a["top5_decisoes_projection"]) == 1
    assert payload_a["top5_decisoes_projection"][0]["title"] == "A"
    assert payload_b["top5_decisoes_projection"] == []

    assert len(payload_a["risks_projection"]) == 1
    assert payload_b["risks_projection"] == []
