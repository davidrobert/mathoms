"""Admin endpoint — top-N campos pedidos pelo LLM (ADR-206 M4)."""

from __future__ import annotations

import pytest

from backend.app.models.planner_field_request import PlannerFieldRequest
from backend.app.models.planner_review import PlannerReview
from backend.tests.factories import make_run, make_user, make_workspace
from backend.tests.helpers.planner_seed import (
    build_e5_artifact,
    build_parecer_artifact,
    build_planner_review,
)

PERSONA_HASH = "c" * 64


async def _with_cookie(client, token: str):
    client.cookies.set("ops_session", token, domain="test", path="/admin")


async def _seed_review_only(db, workspace) -> PlannerReview:
    """Cria review premium para o workspace; sem field_requests anexas."""
    run = await make_run(db, workspace=workspace)
    e5 = build_e5_artifact(workspace.id, run.id)
    parecer = build_parecer_artifact(workspace.id, run.id, content_json={})
    db.add_all([e5, parecer])
    await db.flush()
    review = build_planner_review(
        workspace.id,
        run.id,
        parecer_artifact_id=parecer.id,
        e5_artifact_id=e5.id,
        persona_hash=PERSONA_HASH,
    )
    db.add(review)
    await db.flush()
    return review


async def _seed_review_with_paths(db, workspace, paths: list[str]) -> PlannerReview:
    """Cria review premium + N field requests com paths fornecidos."""
    review = await _seed_review_only(db, workspace)
    for p in paths:
        db.add(
            PlannerFieldRequest(
                workspace_id=workspace.id,
                planner_review_id=review.id,
                field_path=p,
                motivo="motivo de teste",
                reason="llm_declared",
            )
        )
    return review


async def _seed_two_reviews_paths(db, ws) -> None:
    """Helper: 2 reviews com paths repetidos pra agregação."""
    await _seed_review_with_paths(db, ws, ["$.a", "$.b"])
    await _seed_review_with_paths(db, ws, ["$.a"])
    await db.commit()


@pytest.mark.asyncio
async def test_top_endpoint_returns_aggregated_paths(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    """Happy path: 2 reviews, paths repetidos → endpoint retorna agregado."""
    u = await make_user(db)
    ws = await make_workspace(db, owner=u)
    await _seed_two_reviews_paths(db, ws)
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get("/admin/planner-review/field-requests/top?days=30&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["days"] == 30
    assert body["limit"] == 10
    paths = {item["field_path"]: item for item in body["items"]}
    assert "$.a" in paths and "$.b" in paths
    assert paths["$.a"]["frequency"] == 2
    assert paths["$.b"]["frequency"] == 1
    assert paths["$.a"]["workspaces_count"] == 1


@pytest.mark.asyncio
async def test_top_endpoint_empty_state(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    """Sem dados de telemetria → items vazio (não 404)."""
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get("/admin/planner-review/field-requests/top")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []


@pytest.mark.asyncio
async def test_top_endpoint_requires_auth(admin_ui_enabled, ops_yaml, client) -> None:
    """Sem cookie ``ops_session`` → 401."""
    resp = await client.get("/admin/planner-review/field-requests/top")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_top_endpoint_validates_query_params(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client
) -> None:
    """``days`` fora de range → 422 (Query validator)."""
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get("/admin/planner-review/field-requests/top?days=0")
    assert resp.status_code == 422
    resp = await client.get("/admin/planner-review/field-requests/top?limit=999")
    assert resp.status_code == 422
