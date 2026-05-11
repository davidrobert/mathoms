"""Seed: schema + workspace + artefatos E4/E5 + manual overrides."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import Base, SyncSessionLocal, engine
from backend.app.core.security import hash_password
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.transaction_override import (
    OVERRIDE_SOURCE_MANUAL,
    TransactionOverride,
)
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.workspace_member import WorkspaceMember
from backend.app.services.feature_flags_service import set_flag
from backend.app.services.report_publication import publish_month
from backend.app.services.transaction_service import generate_transaction_hash
from dev._dogfood_gate_a12.fixture import split_e4_payload


async def create_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _new_user() -> User:
    return User(
        email="dogfood-gate@mathoms.dev",
        full_name="Dogfood Gate A12",
        hashed_password=hash_password("DogfoodGate123!"),
        is_active=True,
    )


def _new_workspace(owner_id: str) -> Workspace:
    return Workspace(name="Dogfood Gate Workspace", family_surname="Silva", owner_id=owner_id)


async def seed_workspace(db: AsyncSession) -> tuple[str, str]:
    """User + workspace + membership + learning_loop_enabled. Retorna (user_id, ws_id)."""
    user = _new_user()
    db.add(user)
    await db.flush()
    ws = _new_workspace(user.id)
    db.add(ws)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner"))
    await db.flush()
    await set_flag(ws.id, "learning_loop_enabled", True, db=db)
    await db.commit()
    return user.id, ws.id


def make_run(ws_id: str) -> PipelineRun:
    return PipelineRun(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        status=PipelineRunStatus.completed,
        started_at=datetime.now(timezone.utc),
        tier_at_run="premium",
        incremental=False,
        reprocess_all=False,
        total_documents=0,
    )


def _make_e4_artifact(ws_id: str, run_id: str, key: str, payload: dict) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="categorize_transactions",
        artifact_key=key,
        content_json=payload,
    )


async def seed_e4_artifact_with_items(
    db: AsyncSession, ws_id: str, items: list[dict]
) -> PipelineRun:
    run = make_run(ws_id)
    db.add(run)
    await db.flush()
    despesas_payload, receitas_payload = split_e4_payload(items)
    db.add(_make_e4_artifact(ws_id, run.id, "despesas", despesas_payload))
    db.add(_make_e4_artifact(ws_id, run.id, "receitas", receitas_payload))
    await db.commit()
    return run


def _make_analysis_artifact(ws_id: str, run_id: str) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="analyze_finances",
        artifact_key="analise_financeira",
        content_json={"score": 78, "summary": "dogfood gate"},
    )


async def close_months(db: AsyncSession, ws_id: str, periods: list[str]) -> int:
    """Publica analysis artifact e fecha cada ``period`` (mês imutável ADR-187)."""
    run = make_run(ws_id)
    db.add(run)
    await db.flush()
    art = _make_analysis_artifact(ws_id, run.id)
    db.add(art)
    await db.flush()
    artifact_id = art.id
    for p in periods:
        await publish_month(ws_id, p, artifact_id, actor="dogfood:gate", db=db)
    await db.commit()
    return len(periods)


def _build_manual_override(ws_id: str, tx: dict) -> TransactionOverride:
    return TransactionOverride(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        transaction_hash=generate_transaction_hash(tx),
        original_category=tx.get("categoria", "Outros"),
        new_category="Categoria Manual Crítica",
        source=OVERRIDE_SOURCE_MANUAL,
        rule_id=None,
        reviewed=True,
        created_at=datetime.now(timezone.utc),
    )


def seed_manual_overrides_sync(ws_id: str, manual_tx_payloads: list[dict]) -> int:
    if not manual_tx_payloads:
        return 0
    with SyncSessionLocal() as sync_db:
        for tx in manual_tx_payloads:
            sync_db.add(_build_manual_override(ws_id, tx))
        sync_db.commit()
    return len(manual_tx_payloads)


__all__ = [
    "close_months",
    "create_schema",
    "make_run",
    "seed_e4_artifact_with_items",
    "seed_manual_overrides_sync",
    "seed_workspace",
]
