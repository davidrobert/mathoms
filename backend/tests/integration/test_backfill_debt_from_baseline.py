"""Integration test do backfill de Debt (ADR-227 §D6 · Sprint A15 Onda 2)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

import dev.backfill_debt_from_baseline as backfill
from backend.app.core.database import SyncSessionLocal
from backend.app.models import (
    DEBT_SOURCE_BASELINE_IRPF_MIGRATION,
    Debt,
    FamilyMember,
    PipelineArtifact,
)
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.tests import factories


def _divida_for(key: str, saldo: Decimal) -> dict:
    return {
        "descricao": f"Dívida {key}",
        "proprietario": f"{key} silva",
        "saldo_31_12": str(saldo),
    }


def make_baseline_dividas(*member_saldos: tuple[str, Decimal]) -> dict:
    """Baseline minimal — allowlisted P1 fixture helper."""
    return {
        "pipeline_stage": "E1.5_Baseline_Patrimonial",
        "data_processamento": "2026-05-20",
        "dividas": [_divida_for(k, s) for k, s in member_saldos],
    }


def _make_pipeline_run(ws_id: str) -> PipelineRun:
    return PipelineRun(
        id=str(uuid4()),
        workspace_id=ws_id,
        status=PipelineRunStatus.completed,
        started_at=datetime.now(timezone.utc),
        tier_at_run="premium",
        incremental=False,
        reprocess_all=False,
        total_documents=1,
    )


async def make_seed_baseline_artifact(db, ws_id: str, baseline: dict) -> None:
    """Allowlisted P1 fixture helper — cria PipelineRun + PipelineArtifact (consolidate_baseline)."""
    run = _make_pipeline_run(ws_id)
    db.add(run)
    await db.flush()
    db.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=run.id,
            stage="consolidate_baseline",
            artifact_key="baseline_patrimonial",
            content_json=baseline,
        )
    )
    await db.commit()


async def make_seed_member(db, ws_id: str, key: str) -> FamilyMember:
    """Allowlisted P1 fixture helper."""
    fm = FamilyMember(
        workspace_id=ws_id,
        key=key,
        full_name=key.title(),
        short_name=key.title(),
        role="titular",
    )
    db.add(fm)
    await db.flush()
    return fm


async def _seed_two_members_with_dividas(db, ws_id: str) -> None:
    await make_seed_member(db, ws_id, "david")
    await make_seed_member(db, ws_id, "mariana")
    await make_seed_baseline_artifact(
        db,
        ws_id,
        make_baseline_dividas(("david", Decimal("300000.00")), ("mariana", Decimal("25000.50"))),
    )


async def _list_debts(db, ws_id: str) -> list[Debt]:
    result = await db.execute(
        select(Debt).where(Debt.workspace_id == ws_id).order_by(Debt.descricao)
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_dry_run_reports_would_create_for_each_member_with_dividas(db):
    ws = await factories.make_workspace(db)
    await _seed_two_members_with_dividas(db, ws.id)
    with SyncSessionLocal() as session:
        report = backfill._audit_workspace(session, ws.id, dry_run=True)
    assert report["status"] == "would_migrate"
    assert sorted(m["action"] for m in report["members"]) == ["would_create", "would_create"]
    assert await _list_debts(db, ws.id) == []  # dry-run não persiste


@pytest.mark.asyncio
async def test_apply_persists_one_debt_per_member_with_dividas(db):
    ws = await factories.make_workspace(db)
    await _seed_two_members_with_dividas(db, ws.id)
    with SyncSessionLocal() as session:
        report = backfill._audit_workspace(session, ws.id, dry_run=False)
    assert report["status"] == "ok"
    assert sorted(m["action"] for m in report["members"]) == ["created", "created"]
    rows = await _list_debts(db, ws.id)
    assert len(rows) == 2
    assert all(d.source == DEBT_SOURCE_BASELINE_IRPF_MIGRATION for d in rows)
    assert all(d.needs_review and d.property_id is None for d in rows)
    assert {d.descricao for d in rows} == {
        "Migrado de baseline IRPF (david)",
        "Migrado de baseline IRPF (mariana)",
    }


@pytest.mark.asyncio
async def test_idempotency_rerun_apply_is_noop_for_already_migrated(db):
    ws = await factories.make_workspace(db)
    await make_seed_member(db, ws.id, "david")
    await make_seed_baseline_artifact(
        db, ws.id, make_baseline_dividas(("david", Decimal("100000.00")))
    )
    with SyncSessionLocal() as session:
        backfill._audit_workspace(session, ws.id, dry_run=False)
    with SyncSessionLocal() as session:
        report2 = backfill._audit_workspace(session, ws.id, dry_run=False)
    assert report2["status"] == "noop"
    assert [m["action"] for m in report2["members"]] == ["skipped_already_migrated"]
    assert len(await _list_debts(db, ws.id)) == 1


@pytest.mark.asyncio
async def test_workspace_with_zero_dividas_reports_skipped_zero(db):
    ws = await factories.make_workspace(db)
    await make_seed_member(db, ws.id, "david")
    await make_seed_baseline_artifact(db, ws.id, make_baseline_dividas())  # baseline vazio
    with SyncSessionLocal() as session:
        report = backfill._audit_workspace(session, ws.id, dry_run=False)
    assert report["status"] == "noop"
    assert [m["action"] for m in report["members"]] == ["skipped_zero"]
    assert await _list_debts(db, ws.id) == []


@pytest.mark.asyncio
async def test_workspace_without_baseline_artifact_is_skipped(db):
    ws = await factories.make_workspace(db)
    await make_seed_member(db, ws.id, "david")
    await db.commit()
    with SyncSessionLocal() as session:
        report = backfill._audit_workspace(session, ws.id, dry_run=True)
    assert report["status"] == "skip"
    assert report["reason"] == "no_baseline"


def test_brl_to_cents_rounds_half_up():
    """ADR-090: BRL → cents usa HALF_UP, não truncamento de ``int()``."""
    assert backfill._brl_to_cents(0) == 0
    assert backfill._brl_to_cents("100") == 10_000
    assert backfill._brl_to_cents(Decimal("1234.56")) == 123_456
    assert backfill._brl_to_cents(Decimal("999.999")) == 100_000  # half-up → 1.000,00
    assert backfill._brl_to_cents(Decimal("999.994")) == 99_999  # half-up → 999,99


def test_sum_dividas_filters_by_member_key_substring():
    baseline = {
        "dividas": [
            {"proprietario": "David Robert", "saldo_31_12": 100},
            {"proprietario": "Mariana Oliveira", "saldo_31_12": 50},
            {"proprietario": "Outra Pessoa", "saldo_31_12": 999},
        ]
    }
    assert backfill._sum_dividas_for_member(baseline, "david") == Decimal("100")
    assert backfill._sum_dividas_for_member(baseline, "mariana") == Decimal("50")
    assert backfill._sum_dividas_for_member(baseline, "naoexiste") == Decimal("0")
