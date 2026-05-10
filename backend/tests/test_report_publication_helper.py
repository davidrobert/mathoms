"""Unit tests do helper canônico ``is_month_closed`` + serviço (ADR-187)."""

from __future__ import annotations

import pytest

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.services.report_publication import (
    compute_immutable_hash,
    get_active_publication,
    is_month_closed,
    list_publications,
    publish_month,
    unpublish_month,
)
from backend.tests import factories


async def _make_artifact(db, workspace, content: dict | None = None) -> PipelineArtifact:
    run = await factories.make_run(db, workspace=workspace)
    artifact = PipelineArtifact(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        stage="analyze_finances",
        artifact_key="analise_financeira",
        content_json=content or {"score": 78, "patrimonio_liquido": 250_000.0},
    )
    db.add(artifact)
    await db.flush()
    return artifact


# ─── compute_immutable_hash ───────────────────────────────────────────


def test_hash_is_deterministic_for_same_payload():
    snap = {"a": 1, "b": [2, 3], "c": {"d": "x"}}
    assert compute_immutable_hash(snap) == compute_immutable_hash(snap)


def test_hash_ignores_key_order():
    a = {"a": 1, "b": 2}
    b = {"b": 2, "a": 1}
    assert compute_immutable_hash(a) == compute_immutable_hash(b)


def test_hash_ignores_volatile_keys():
    a = {"score": 78, "generated_at": "2026-05-10T10:00:00Z"}
    b = {"score": 78, "generated_at": "2026-05-10T11:00:00Z"}
    assert compute_immutable_hash(a) == compute_immutable_hash(b)


def test_hash_strips_volatile_keys_recursively():
    a = {"meta": {"rendered_at": "x", "value": 1}}
    b = {"meta": {"rendered_at": "y", "value": 1}}
    assert compute_immutable_hash(a) == compute_immutable_hash(b)


def test_hash_changes_when_content_differs():
    a = {"score": 78}
    b = {"score": 79}
    assert compute_immutable_hash(a) != compute_immutable_hash(b)


# ─── is_month_closed ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_is_month_closed_returns_false_when_no_publication(db):
    ws = await factories.make_workspace(db)
    await db.commit()
    assert await is_month_closed(ws.id, "202601", db=db) is False


@pytest.mark.asyncio
async def test_is_month_closed_returns_true_after_publish(db):
    ws = await factories.make_workspace(db)
    artifact = await _make_artifact(db, ws)
    await publish_month(ws.id, "202601", artifact.id, actor="user:test", db=db)
    await db.commit()
    assert await is_month_closed(ws.id, "202601", db=db) is True


@pytest.mark.asyncio
async def test_is_month_closed_returns_false_after_unpublish(db):
    ws = await factories.make_workspace(db)
    artifact = await _make_artifact(db, ws)
    await publish_month(ws.id, "202601", artifact.id, actor="user:test", db=db)
    await unpublish_month(ws.id, "202601", actor="user:test", db=db)
    await db.commit()
    assert await is_month_closed(ws.id, "202601", db=db) is False


@pytest.mark.asyncio
async def test_is_month_closed_with_revoked_then_republished(db):
    """Linha viva mais recente vence histórico revogado."""
    ws = await factories.make_workspace(db)
    artifact = await _make_artifact(db, ws)
    await publish_month(ws.id, "202601", artifact.id, actor="user:test", db=db)
    await unpublish_month(ws.id, "202601", actor="user:test", db=db)
    await publish_month(ws.id, "202601", artifact.id, actor="user:test", db=db)
    await db.commit()
    assert await is_month_closed(ws.id, "202601", db=db) is True


@pytest.mark.asyncio
async def test_is_month_closed_isolates_workspaces(db):
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    artifact_a = await _make_artifact(db, ws_a)
    await publish_month(ws_a.id, "202601", artifact_a.id, actor="user:a", db=db)
    await db.commit()
    assert await is_month_closed(ws_a.id, "202601", db=db) is True
    assert await is_month_closed(ws_b.id, "202601", db=db) is False


@pytest.mark.asyncio
async def test_is_month_closed_validates_period_format(db):
    ws = await factories.make_workspace(db)
    await db.commit()
    with pytest.raises(ValidationError):
        await is_month_closed(ws.id, "2026-01", db=db)
    with pytest.raises(ValidationError):
        await is_month_closed(ws.id, "20261", db=db)


# ─── publish_month ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_month_creates_row_with_hash(db):
    ws = await factories.make_workspace(db)
    artifact = await _make_artifact(db, ws, content={"score": 78})

    publication = await publish_month(ws.id, "202601", artifact.id, actor="user:test", db=db)
    await db.commit()

    assert publication.workspace_id == ws.id
    assert publication.period_yyyymm == "202601"
    assert publication.artifact_id == artifact.id
    assert publication.unpublished_at is None
    assert publication.immutable_hash == compute_immutable_hash({"score": 78})
    assert publication.published_by == "user:test"


@pytest.mark.asyncio
async def test_publish_month_409_when_already_published(db):
    ws = await factories.make_workspace(db)
    artifact = await _make_artifact(db, ws)
    await publish_month(ws.id, "202601", artifact.id, actor="user:a", db=db)
    with pytest.raises(ConflictError):
        await publish_month(ws.id, "202601", artifact.id, actor="user:b", db=db)


@pytest.mark.asyncio
async def test_publish_month_404_when_artifact_belongs_to_other_workspace(db):
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    artifact_b = await _make_artifact(db, ws_b)
    with pytest.raises(NotFoundError):
        await publish_month(ws_a.id, "202601", artifact_b.id, actor="user:test", db=db)


@pytest.mark.asyncio
async def test_publish_month_404_when_artifact_does_not_exist(db):
    ws = await factories.make_workspace(db)
    await db.commit()
    with pytest.raises(NotFoundError):
        await publish_month(ws.id, "202601", artifact_id=999_999, actor="user:test", db=db)


# ─── unpublish_month ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unpublish_month_409_when_not_published(db):
    ws = await factories.make_workspace(db)
    await db.commit()
    with pytest.raises(ConflictError):
        await unpublish_month(ws.id, "202601", actor="user:test", db=db)


@pytest.mark.asyncio
async def test_unpublish_then_publish_keeps_two_rows(db):
    ws = await factories.make_workspace(db)
    artifact = await _make_artifact(db, ws)

    await publish_month(ws.id, "202601", artifact.id, actor="user:test", db=db)
    await unpublish_month(ws.id, "202601", actor="user:test", db=db)
    await publish_month(ws.id, "202601", artifact.id, actor="user:test", db=db)
    await db.commit()

    publications = await list_publications(ws.id, db=db)
    assert len(publications) == 2
    revoked = [p for p in publications if p.unpublished_at is not None]
    live = [p for p in publications if p.unpublished_at is None]
    assert len(revoked) == 1
    assert len(live) == 1


# ─── get_active_publication ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_active_publication_returns_live_row(db):
    ws = await factories.make_workspace(db)
    artifact = await _make_artifact(db, ws)
    pub = await publish_month(ws.id, "202601", artifact.id, actor="user:test", db=db)
    await db.commit()

    active = await get_active_publication(ws.id, "202601", db=db)
    assert active is not None
    assert active.id == pub.id


@pytest.mark.asyncio
async def test_get_active_publication_returns_none_when_revoked(db):
    ws = await factories.make_workspace(db)
    artifact = await _make_artifact(db, ws)
    await publish_month(ws.id, "202601", artifact.id, actor="user:test", db=db)
    await unpublish_month(ws.id, "202601", actor="user:test", db=db)
    await db.commit()

    assert await get_active_publication(ws.id, "202601", db=db) is None
