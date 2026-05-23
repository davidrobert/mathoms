"""Testes do goal type ``RESERVA_EMERGENCIA`` (ADR-263): INV1, schema, compute, CRUD versionado."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from backend.app.models.goal import VALID_GOAL_TYPES
from backend.app.repositories.goal_repository import GoalRepository
from backend.app.schemas.dto.goal import (
    ReservaEmergenciaGoalDerived,
    ReservaEmergenciaGoalInputs,
)
from backend.app.services.goal_service import (
    compute_reserva_emergencia_derived,
    create_goal_version,
)
from backend.tests import factories

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "schemas"
    / "goal.reserva_emergencia.schema.json"
)


@pytest.fixture(scope="module")
def schema_validator() -> Draft202012Validator:
    with _SCHEMA_PATH.open() as fp:
        return Draft202012Validator(json.load(fp))


# ════════════════════════════════════════════════════════════════════
# Frozenset + DTO Pydantic
# ════════════════════════════════════════════════════════════════════


def test_reserva_emergencia_in_valid_goal_types():
    """ADR-263: tipo registrado em VALID_GOAL_TYPES."""
    assert "RESERVA_EMERGENCIA" in VALID_GOAL_TYPES


def test_inputs_rejects_meses_below_min():
    """INV1: meses_alvo ≥ 3."""
    with pytest.raises(ValidationError):
        ReservaEmergenciaGoalInputs(meses_alvo=2, fonte_despesa_essencial="e5_derived")


def test_inputs_rejects_meses_above_max():
    """INV1: meses_alvo ≤ 18 (acima é hoarding)."""
    with pytest.raises(ValidationError):
        ReservaEmergenciaGoalInputs(meses_alvo=24, fonte_despesa_essencial="e5_derived")


def test_inputs_user_declared_requires_value():
    """fonte=user_declared sem campo declarado → ValidationError."""
    with pytest.raises(ValidationError, match="user_declared"):
        ReservaEmergenciaGoalInputs(meses_alvo=6, fonte_despesa_essencial="user_declared")


def test_inputs_e5_derived_accepts_no_declared():
    """fonte=e5_derived é válido sem declarar (caller passa de E5)."""
    inputs = ReservaEmergenciaGoalInputs(meses_alvo=6, fonte_despesa_essencial="e5_derived")
    assert inputs.meses_alvo == 6
    assert inputs.despesa_essencial_mensal_brl_declared is None


# ════════════════════════════════════════════════════════════════════
# Schema JSON canônico
# ════════════════════════════════════════════════════════════════════


def test_schema_valid_e5_derived(schema_validator):
    doc = {
        "meta_version": 1,
        "inputs": {"meses_alvo": 6, "fonte_despesa_essencial": "e5_derived"},
        "derived": {
            "valor_alvo_brl": 60000.0,
            "valor_atual_brl": 30000.0,
            "cobertura_meses_atual": 3.0,
            "gap_brl": 30000.0,
            "despesa_essencial_mensal_brl": 10000.0,
            "source_e5_run_id": "run-abc",
        },
    }
    errors = list(schema_validator.iter_errors(doc))
    assert errors == []


def test_schema_invalid_meses_out_of_range(schema_validator):
    doc = {
        "meta_version": 1,
        "inputs": {"meses_alvo": 2, "fonte_despesa_essencial": "e5_derived"},
        "derived": {
            "valor_alvo_brl": 0,
            "valor_atual_brl": 0,
            "cobertura_meses_atual": 0,
            "gap_brl": 0,
            "despesa_essencial_mensal_brl": 1.0,
        },
    }
    errors = list(schema_validator.iter_errors(doc))
    assert any("meses_alvo" in str(e.path) or "minimum" in e.message for e in errors)


def test_schema_user_declared_requires_value(schema_validator):
    doc = {
        "meta_version": 1,
        "inputs": {
            "meses_alvo": 6,
            "fonte_despesa_essencial": "user_declared",
        },
        "derived": {
            "valor_alvo_brl": 0,
            "valor_atual_brl": 0,
            "cobertura_meses_atual": 0,
            "gap_brl": 0,
            "despesa_essencial_mensal_brl": 1.0,
        },
    }
    errors = list(schema_validator.iter_errors(doc))
    assert errors, "expected validation error when user_declared sem despesa"


# ════════════════════════════════════════════════════════════════════
# compute_reserva_emergencia_derived (função pura)
# ════════════════════════════════════════════════════════════════════


def test_compute_user_declared_basic():
    inputs = ReservaEmergenciaGoalInputs(
        meses_alvo=6,
        fonte_despesa_essencial="user_declared",
        despesa_essencial_mensal_brl_declared=Decimal("10000"),
    )
    out = compute_reserva_emergencia_derived(
        inputs,
        patrimonio_acessivel_brl=Decimal("30000"),
    )
    assert out.valor_alvo_brl == Decimal("60000.00")
    assert out.valor_atual_brl == Decimal("30000.00")
    assert out.cobertura_meses_atual == pytest.approx(3.0)
    assert out.gap_brl == Decimal("30000.00")
    assert out.despesa_essencial_mensal_brl == Decimal("10000.00")
    assert out.source_e5_run_id is None


def test_compute_e5_derived_uses_passed_value():
    inputs = ReservaEmergenciaGoalInputs(meses_alvo=6, fonte_despesa_essencial="e5_derived")
    out = compute_reserva_emergencia_derived(
        inputs,
        despesa_essencial_mensal_brl_from_e5=Decimal("8500"),
        patrimonio_acessivel_brl=Decimal("60000"),
        source_e5_run_id="run-xyz",
    )
    assert out.valor_alvo_brl == Decimal("51000.00")
    assert out.valor_atual_brl == Decimal("60000.00")
    # cobertura > meses_alvo → gap negativo
    assert out.gap_brl == Decimal("-9000.00")
    assert out.source_e5_run_id == "run-xyz"


def test_compute_e5_derived_without_value_raises():
    """fonte=e5_derived com E5 ausente → ValueError (gate de configuração)."""
    inputs = ReservaEmergenciaGoalInputs(meses_alvo=6, fonte_despesa_essencial="e5_derived")
    with pytest.raises(ValueError, match="e5_derived"):
        compute_reserva_emergencia_derived(inputs)


def test_compute_zero_patrimonio_gap_equals_alvo():
    inputs = ReservaEmergenciaGoalInputs(
        meses_alvo=12,
        fonte_despesa_essencial="user_declared",
        despesa_essencial_mensal_brl_declared=Decimal("5000"),
    )
    out = compute_reserva_emergencia_derived(inputs)
    assert out.valor_alvo_brl == Decimal("60000.00")
    assert out.valor_atual_brl == Decimal("0.00")
    assert out.cobertura_meses_atual == pytest.approx(0.0)
    assert out.gap_brl == Decimal("60000.00")


# ════════════════════════════════════════════════════════════════════
# CRUD versionado (DB)
# ════════════════════════════════════════════════════════════════════


async def _persist_reserva_version(
    db, ws_id, user_id, meses_alvo, despesa, patrimonio, *, effective_from=None
):
    inputs = ReservaEmergenciaGoalInputs(
        meses_alvo=meses_alvo,
        fonte_despesa_essencial="user_declared",
        despesa_essencial_mensal_brl_declared=despesa,
    )
    derived = compute_reserva_emergencia_derived(inputs, patrimonio_acessivel_brl=patrimonio)
    g = await create_goal_version(
        ws_id,
        "RESERVA_EMERGENCIA",
        inputs,
        derived,
        db=db,
        created_by=user_id,
        effective_from=effective_from,
    )
    await db.commit()
    return g


@pytest.mark.asyncio
async def test_create_and_revision(db):
    """Edição cria nova revisão e fecha a anterior (ADR-073 invariante)."""
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)

    g1 = await _persist_reserva_version(db, ws.id, user.id, 6, Decimal("8000"), Decimal("0"))
    assert g1.effective_to is None
    assert g1.derived_json["valor_alvo_brl"] == 48000.0

    eff2 = date.today() + timedelta(days=1)
    g2 = await _persist_reserva_version(
        db, ws.id, user.id, 12, Decimal("8000"), Decimal("12000"), effective_from=eff2
    )

    await db.refresh(g1)
    await db.refresh(g2)
    assert g1.effective_to == eff2 - timedelta(days=1)
    assert g2.effective_to is None
    assert g2.derived_json["valor_alvo_brl"] == 96000.0


@pytest.mark.asyncio
async def test_repository_accepts_reserva_emergencia_type(db):
    """GoalRepository valida `goal_type` contra VALID_GOAL_TYPES (smoke)."""
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)

    repo = GoalRepository(db)
    # Não levanta — RESERVA_EMERGENCIA está em VALID_GOAL_TYPES.
    current = await repo.get_active_by_type(ws.id, "RESERVA_EMERGENCIA")
    assert current is None


# ════════════════════════════════════════════════════════════════════
# Mapper ORM → DTO
# ════════════════════════════════════════════════════════════════════


def test_mapper_registers_reserva_emergencia():
    from backend.app.schemas.dto.goal import GOAL_TYPE_DTO_CLASSES

    assert "RESERVA_EMERGENCIA" in GOAL_TYPE_DTO_CLASSES
    response_cls, inputs_cls, derived_cls = GOAL_TYPE_DTO_CLASSES["RESERVA_EMERGENCIA"]
    assert inputs_cls is ReservaEmergenciaGoalInputs
    assert derived_cls is ReservaEmergenciaGoalDerived
