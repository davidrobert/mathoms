"""Testes do ``GoalsBundle`` — shape, fallback empty workspace, tenancy (ADR-180, A10.6)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app.models.decision import Decision
from backend.app.models.goal import VALID_GOAL_TYPES
from backend.app.models.risk import Risk
from backend.app.services.pipeline.pipeline_adapter import (
    build_config_overrides_from_db,
    build_goals_payload,
    build_goals_payload_sync,
)
from backend.tests import factories

# ════════════════════════════════════════════════════════════════════
# Shape básico do GoalsBundle
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_empty_workspace_returns_minimal_bundle(db):
    """Workspace sem aggregates retorna bundle mínimo (versão + projeções vazias)."""
    ws = await factories.make_workspace(db)
    bundle = await build_goals_payload(ws.id, db=db)
    assert bundle["_adapter_version"] == 2
    assert bundle["top5_decisoes_projection"] == []
    assert bundle["risks_projection"] == []
    # Goal sections ausentes quando workspace vazio.
    assert "independencia_financeira" not in bundle
    assert "aportes" not in bundle
    assert "dolarizacao" not in bundle
    assert "alocacao_alvo" not in bundle


@pytest.mark.asyncio
async def test_bundle_contains_if_goal_section(db):
    """Goal IF vigente popula seção ``independencia_financeira``."""
    ws = await factories.make_workspace(db)
    await factories.make_if_goal(
        db,
        workspace=ws,
        renda_passiva_mensal_brl=Decimal("25000"),
        trs_pct=5.0,
    )
    await db.commit()

    bundle = await build_goals_payload(ws.id, db=db)
    section = bundle["independencia_financeira"]
    assert section["_ref"] == "D15"
    assert section["if_meta"] == 6_000_000.0
    assert section["trs_pct"] == 5.0
    assert section["renda_passiva_meta_mensal"] == 25000


# ════════════════════════════════════════════════════════════════════
# Tenancy
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_bundles_isolated_between_workspaces(db):
    """Bundle de WS-A não vaza dados de WS-B."""
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    await factories.make_if_goal(db, workspace=ws_a, renda_passiva_mensal_brl=Decimal("10000"))
    await db.commit()

    bundle_a = await build_goals_payload(ws_a.id, db=db)
    bundle_b = await build_goals_payload(ws_b.id, db=db)
    assert "independencia_financeira" in bundle_a
    assert "independencia_financeira" not in bundle_b


# ════════════════════════════════════════════════════════════════════
# Projeções A10.5 — Decision/Risk integradas no bundle
# ════════════════════════════════════════════════════════════════════


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


@pytest.mark.asyncio
async def test_bundle_includes_top5_decisions_projection(db):
    ws = await factories.make_workspace(db)
    db.add(_make_decision(ws.id, code="D02", title="Aporte mensal", impact_1y_brl_cents=24_000_000))
    await db.commit()

    bundle = await build_goals_payload(ws.id, db=db)
    items = bundle["top5_decisoes_projection"]
    assert len(items) == 1
    assert items[0]["title"] == "Aporte mensal"
    assert items[0]["impact_1y_brl_cents"] == 24_000_000


@pytest.mark.asyncio
async def test_bundle_includes_risks_projection(db):
    ws = await factories.make_workspace(db)
    db.add(
        _make_risk(ws.id, code="morte", name="Morte", impact_level="crítico", probability="alta")
    )
    await db.commit()

    bundle = await build_goals_payload(ws.id, db=db)
    items = bundle["risks_projection"]
    assert len(items) == 1
    assert items[0]["name"] == "Morte"
    assert items[0]["impact_level"] == "crítico"


# ════════════════════════════════════════════════════════════════════
# Sync vs Async — paridade
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_sync_bundle_minimal_workspace_shape(db):
    """Sync version funciona em isolamento (worker Celery path)."""
    from backend.app.core.database import SyncSessionLocal

    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as sync_db:
        bundle = build_goals_payload_sync(ws.id, db=sync_db)

    assert bundle["_adapter_version"] == 2
    assert bundle["top5_decisoes_projection"] == []
    assert bundle["risks_projection"] == []
    # Confirma que TypedDict aceita o dict como-é (runtime: pure dict).
    assert isinstance(bundle, dict)


# ════════════════════════════════════════════════════════════════════
# build_config_overrides_from_db inclui goals.json (ADR-180)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_overrides_includes_goals_json_key(db):
    """``build_config_overrides_from_db`` injeta ``goals.json`` para ``ctx.load_config``."""
    from backend.app.core.database import SyncSessionLocal

    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as sync_db:
        overrides = build_config_overrides_from_db(ws.id, db=sync_db)

    assert "goals.json" in overrides, (
        "ADR-180: goals.json deve aparecer em overrides para que "
        "ctx.load_config('goals.json') retorne o GoalsBundle"
    )
    assert isinstance(overrides["goals.json"], dict)
    assert overrides["goals.json"]["_adapter_version"] == 2


# ════════════════════════════════════════════════════════════════════
# PLANNING_CONTEXT removido (Sprint A10.6 cleanup)
# ════════════════════════════════════════════════════════════════════


def test_planning_context_removed_from_valid_goal_types() -> None:
    """ADR-180 cleanup: ``PLANNING_CONTEXT`` removido de ``VALID_GOAL_TYPES``."""
    assert "PLANNING_CONTEXT" not in VALID_GOAL_TYPES, (
        "PLANNING_CONTEXT deve ser removido em A10.6 — bag genérica era resíduo"
        " da fase de cutover; campos migraram para Decision/Risk/business_profile."
    )
