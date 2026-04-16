"""Testes de integração da API de Tasks e TaskSuggestions (ADR-074)."""

from __future__ import annotations

import pytest

from backend.app.core.security import create_access_token
from backend.tests import factories


TASK_BODY = {
    "title": "Cotar seguro vida",
    "category": "Seguros",
    "priority": "S",
    "deadline_kind": "MONTH",
    "deadline_label": "Abr/2026",
}


async def _make_auth(db, client):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return user, ws


# ─── CRUD ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_task_201(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/tasks", json=TASK_BODY
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Cotar seguro vida"
    assert data["priority"] == "S"
    assert data["status"] == "pending"
    assert data["number"] == 1


@pytest.mark.asyncio
async def test_list_tasks_empty_initially(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.get(f"/api/workspaces/{ws.id}/tasks")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_tasks_after_create(db, client):
    _, ws = await _make_auth(db, client)
    await client.post(f"/api/workspaces/{ws.id}/tasks", json=TASK_BODY)
    await client.post(
        f"/api/workspaces/{ws.id}/tasks",
        json={**TASK_BODY, "title": "Outra", "priority": "R"},
    )
    resp = await client.get(f"/api/workspaces/{ws.id}/tasks")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_transition_status_endpoint(db, client):
    _, ws = await _make_auth(db, client)
    r = await client.post(f"/api/workspaces/{ws.id}/tasks", json=TASK_BODY)
    task_id = r.json()["id"]

    resp = await client.post(
        f"/api/workspaces/{ws.id}/tasks/{task_id}/status",
        json={"status": "done", "status_reason": "concluído"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_patch_task_updates_fields(db, client):
    _, ws = await _make_auth(db, client)
    r = await client.post(f"/api/workspaces/{ws.id}/tasks", json=TASK_BODY)
    task_id = r.json()["id"]

    resp = await client.patch(
        f"/api/workspaces/{ws.id}/tasks/{task_id}",
        json={"title": "Título editado", "priority": "R"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Título editado"
    assert data["priority"] == "R"


@pytest.mark.asyncio
async def test_delete_task_transitions_to_cancelled(db, client):
    _, ws = await _make_auth(db, client)
    r = await client.post(f"/api/workspaces/{ws.id}/tasks", json=TASK_BODY)
    task_id = r.json()["id"]

    resp = await client.delete(f"/api/workspaces/{ws.id}/tasks/{task_id}")
    assert resp.status_code == 204

    # Task ainda existe, agora cancelled
    resp = await client.get(f"/api/workspaces/{ws.id}/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_upcoming_tasks_endpoint(db, client):
    from datetime import date, timedelta

    _, ws = await _make_auth(db, client)
    # Task com deadline amanhã (dentro dos 7 dias)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    await client.post(
        f"/api/workspaces/{ws.id}/tasks",
        json={
            **TASK_BODY,
            "title": "Amanhã",
            "deadline_kind": "HARD_DATE",
            "deadline_date": tomorrow,
        },
    )
    # Task com deadline em 30 dias (fora)
    in_30 = (date.today() + timedelta(days=30)).isoformat()
    await client.post(
        f"/api/workspaces/{ws.id}/tasks",
        json={
            **TASK_BODY,
            "title": "30 dias",
            "deadline_kind": "HARD_DATE",
            "deadline_date": in_30,
        },
    )

    resp = await client.get(f"/api/workspaces/{ws.id}/tasks/upcoming?days=7")
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()["tasks"]]
    assert "Amanhã" in titles
    assert "30 dias" not in titles


@pytest.mark.asyncio
async def test_export_markdown_endpoint(db, client):
    _, ws = await _make_auth(db, client)
    await client.post(f"/api/workspaces/{ws.id}/tasks", json=TASK_BODY)

    resp = await client.get(f"/api/workspaces/{ws.id}/tasks/export.md")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    body = resp.text
    assert "Essenciais (S)" in body
    assert "Cotar seguro vida" in body


# ─── Validação ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_rejects_invalid_priority(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/tasks",
        json={**TASK_BODY, "priority": "X"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_invalid_category(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/tasks",
        json={**TASK_BODY, "category": "InvalidCategory"},
    )
    assert resp.status_code == 422


# ─── Multi-tenant isolation ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_list_returns_403(db, client):
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    await factories.make_task(db, workspace=ws_b)
    await db.commit()

    token_a = create_access_token(user_a.id)
    client.headers["Authorization"] = f"Bearer {token_a}"

    resp = await client.get(f"/api/workspaces/{ws_b.id}/tasks")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_create_returns_403(db, client):
    user_a = await factories.make_user(db)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    await db.commit()

    token_a = create_access_token(user_a.id)
    client.headers["Authorization"] = f"Bearer {token_a}"
    resp = await client.post(
        f"/api/workspaces/{ws_b.id}/tasks", json=TASK_BODY
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_task_ids_do_not_leak_across_workspaces(db, client):
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    t_b = await factories.make_task(db, workspace=ws_b)
    await db.commit()

    token_a = create_access_token(user_a.id)
    client.headers["Authorization"] = f"Bearer {token_a}"
    # User A tenta pegar task que é do workspace B mas usando ws_a.id — 404 (task
    # não está no ws_a)
    resp = await client.get(f"/api/workspaces/{ws_a.id}/tasks/{t_b.id}")
    assert resp.status_code == 404


# ─── Suggestions ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_suggestions(db, client):
    _, ws = await _make_auth(db, client)
    await factories.make_task_suggestion(db, workspace=ws)
    await db.commit()
    resp = await client.get(f"/api/workspaces/{ws.id}/task-suggestions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_approve_suggestion_creates_task(db, client):
    _, ws = await _make_auth(db, client)
    sugg = await factories.make_task_suggestion(
        db,
        workspace=ws,
        proposed_payload={
            "title": "Sugerido pela LLM",
            "category": "Tributario",
            "priority": "R",
            "deadline_kind": "UNSCHEDULED",
        },
    )
    await db.commit()

    resp = await client.post(
        f"/api/workspaces/{ws.id}/task-suggestions/{sugg.id}/approve",
        json={},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Sugerido pela LLM"
    assert data["created_from"] == "llm_suggestion"
    assert data["source_suggestion_id"] == sugg.id


@pytest.mark.asyncio
async def test_reject_suggestion(db, client):
    _, ws = await _make_auth(db, client)
    sugg = await factories.make_task_suggestion(db, workspace=ws)
    await db.commit()
    resp = await client.post(
        f"/api/workspaces/{ws.id}/task-suggestions/{sugg.id}/reject",
        json={"reason": "não relevante agora"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_post_suggestion_creates_pending(db, client):
    """POST /task-suggestions — E5.N escreve sugestão via HTTP."""
    _, ws = await _make_auth(db, client)
    body = {
        "proposed_payload": {
            "title": "Consultar CPA antes de virar US resident",
            "category": "Tributario",
            "priority": "R",
            "deadline_kind": "QUARTER",
            "deadline_label": "T3/26",
        },
        "source": "e5n_llm",
        "source_run_id": "run-xyz-123",
    }
    resp = await client.post(
        f"/api/workspaces/{ws.id}/task-suggestions", json=body
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["source"] == "e5n_llm"
    assert data["proposed_payload"]["title"].startswith("Consultar CPA")


@pytest.mark.asyncio
async def test_post_suggestion_cross_tenant_returns_403(db, client):
    user_a = await factories.make_user(db)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    await db.commit()
    token_a = create_access_token(user_a.id)
    client.headers["Authorization"] = f"Bearer {token_a}"

    body = {
        "proposed_payload": {
            "title": "tentativa maliciosa",
            "category": "Orcamento",
            "priority": "O",
        },
        "source": "e5n_llm",
    }
    resp = await client.post(
        f"/api/workspaces/{ws_b.id}/task-suggestions", json=body
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_scan_deadlines_endpoint_creates_notifications(db, client):
    from datetime import date, timedelta

    _, ws = await _make_auth(db, client)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    await client.post(
        f"/api/workspaces/{ws.id}/tasks",
        json={
            "title": "Urgente",
            "category": "Seguros",
            "priority": "S",
            "deadline_kind": "HARD_DATE",
            "deadline_date": tomorrow,
        },
    )

    resp = await client.post(f"/api/workspaces/{ws.id}/tasks/scan-deadlines")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["created"] == 1
    assert stats["evaluated"] == 1


# ─── Task↔Goal (F8.3) ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_tasks_for_goal_returns_only_linked(db, client):
    _, ws = await _make_auth(db, client)
    goal = await factories.make_if_goal(db, workspace=ws)
    # Task ligada à meta
    linked = await factories.make_task(
        db, workspace=ws, title="Ligada à meta"
    )
    linked.related_goal_id = goal.id
    db.add(linked)
    # Task não-ligada
    await factories.make_task(db, workspace=ws, title="Sem meta")
    await db.commit()

    resp = await client.get(f"/api/workspaces/{ws.id}/goals/{goal.id}/tasks")
    assert resp.status_code == 200
    data = resp.json()
    titles = [t["title"] for t in data["tasks"]]
    assert titles == ["Ligada à meta"]
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_tasks_for_goal_cross_tenant_403(db, client):
    user_a = await factories.make_user(db)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    goal_b = await factories.make_if_goal(db, workspace=ws_b)
    await db.commit()

    token_a = create_access_token(user_a.id)
    client.headers["Authorization"] = f"Bearer {token_a}"
    resp = await client.get(f"/api/workspaces/{ws_b.id}/goals/{goal_b.id}/tasks")
    assert resp.status_code == 403


# ─── Task Progress (F8.3) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_progress_endpoint_returns_not_trackable(db, client):
    _, ws = await _make_auth(db, client)
    r = await client.post(
        f"/api/workspaces/{ws.id}/tasks",
        json={
            "title": "Entregar IRPF 2026",
            "category": "Tributario",
            "priority": "S",
        },
    )
    task_id = r.json()["id"]

    resp = await client.get(f"/api/workspaces/{ws.id}/tasks/{task_id}/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_trackable"] is False


@pytest.mark.asyncio
async def test_task_progress_endpoint_returns_trackable_for_aporte(db, client):
    _, ws = await _make_auth(db, client)
    r = await client.post(
        f"/api/workspaces/{ws.id}/tasks",
        json={
            "title": "Configurar aporte R$ 20.000/mês",
            "category": "Invest",
            "priority": "S",
        },
    )
    task_id = r.json()["id"]

    resp = await client.get(f"/api/workspaces/{ws.id}/tasks/{task_id}/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_trackable"] is True
    assert data["target_brl"] == 20000.0


@pytest.mark.asyncio
async def test_filter_tasks_by_related_goal_id(db, client):
    _, ws = await _make_auth(db, client)
    goal = await factories.make_if_goal(db, workspace=ws)
    t = await factories.make_task(db, workspace=ws, title="Ligada")
    t.related_goal_id = goal.id
    db.add(t)
    await factories.make_task(db, workspace=ws, title="Sem link")
    await db.commit()

    resp = await client.get(
        f"/api/workspaces/{ws.id}/tasks?related_goal_id={goal.id}"
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
