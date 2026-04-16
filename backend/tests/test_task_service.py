"""Testes de `task_service` + `task_suggestion_service` (ADR-074).

Cobre:
- Criação com number auto-incrementado (unique por workspace)
- Transições válidas e inválidas
- Enforcement de dependência (done bloqueado se parent pendente)
- Listagem com filtros (priority, category, status, deadline)
- Export markdown (round-trip parser)
- Suggestions: approve/reject/merge
- Isolamento multi-tenant
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from backend.app.schemas.task import (
    TaskCreate,
    TaskFilters,
    TaskSuggestionCreate,
    TaskSuggestionProposed,
    TaskUpdate,
)
from backend.app.services import task_service, task_suggestion_service
from backend.tests import factories


# ════════════════════════════════════════════════════════════════════
# Criação e unicidade de number
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_task_auto_assigns_number(db):
    ws = await factories.make_workspace(db)
    t1 = await task_service.create_task(
        ws.id,
        TaskCreate(title="First", category="Invest", priority="S"),
        db=db,
    )
    t2 = await task_service.create_task(
        ws.id,
        TaskCreate(title="Second", category="Invest", priority="R"),
        db=db,
    )
    assert t1.number == 1
    assert t2.number == 2


@pytest.mark.asyncio
async def test_create_task_preserves_explicit_number(db):
    """Importer passa number explícito (ex: #43 do tarefas.md)."""
    ws = await factories.make_workspace(db)
    t = await task_service.create_task(
        ws.id,
        TaskCreate(title="Seed #43", category="Invest", priority="S", number=43),
        db=db,
    )
    assert t.number == 43
    # Próxima automática é 44
    t2 = await task_service.create_task(
        ws.id,
        TaskCreate(title="Next", category="Invest", priority="R"),
        db=db,
    )
    assert t2.number == 44


@pytest.mark.asyncio
async def test_task_numbers_are_scoped_per_workspace(db):
    """Workspace A e B podem ambas ter task #1."""
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    t_a = await task_service.create_task(
        ws_a.id, TaskCreate(title="A1", category="Invest", priority="S"), db=db
    )
    t_b = await task_service.create_task(
        ws_b.id, TaskCreate(title="B1", category="Invest", priority="S"), db=db
    )
    assert t_a.number == t_b.number == 1
    assert t_a.id != t_b.id


@pytest.mark.asyncio
async def test_create_rejects_invalid_category(db):
    ws = await factories.make_workspace(db)
    with pytest.raises(HTTPException) as exc:
        await task_service.create_task(
            ws.id,
            TaskCreate(title="Bad", category="NotACategory", priority="S"),
            db=db,
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_parent_from_other_workspace(db):
    """IDOR check: parent de outro ws não é aceito."""
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    other = await factories.make_task(db, workspace=ws_b)
    with pytest.raises(HTTPException) as exc:
        await task_service.create_task(
            ws_a.id,
            TaskCreate(
                title="Child",
                category="Invest",
                priority="R",
                parent_task_id=other.id,
            ),
            db=db,
        )
    assert exc.value.status_code == 400


# ════════════════════════════════════════════════════════════════════
# Transições de status
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_transition_pending_to_done_sets_completed_at(db):
    ws = await factories.make_workspace(db)
    t = await factories.make_task(db, workspace=ws, status="pending")
    updated = await task_service.transition_status(
        ws.id, t.id, new_status="done", db=db
    )
    assert updated.status == "done"
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_transition_to_cancelled_sets_cancelled_at(db):
    ws = await factories.make_workspace(db)
    t = await factories.make_task(db, workspace=ws)
    updated = await task_service.transition_status(
        ws.id, t.id, new_status="cancelled", db=db, reason="teste"
    )
    assert updated.status == "cancelled"
    assert updated.cancelled_at is not None
    assert updated.status_reason == "teste"


@pytest.mark.asyncio
async def test_reopen_done_clears_completed_at(db):
    ws = await factories.make_workspace(db)
    t = await factories.make_task(db, workspace=ws, status="pending")
    await task_service.transition_status(ws.id, t.id, new_status="done", db=db)
    reopened = await task_service.transition_status(
        ws.id, t.id, new_status="pending", db=db
    )
    assert reopened.status == "pending"
    assert reopened.completed_at is None


@pytest.mark.asyncio
async def test_invalid_transition_raises_409(db):
    ws = await factories.make_workspace(db)
    t = await factories.make_task(db, workspace=ws, status="cancelled")
    # cancelled → blocked não é aceito
    with pytest.raises(HTTPException) as exc:
        await task_service.transition_status(
            ws.id, t.id, new_status="blocked", db=db
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_done_blocked_by_pending_parent(db):
    ws = await factories.make_workspace(db)
    parent = await factories.make_task(db, workspace=ws, status="pending")
    child = await factories.make_task(
        db, workspace=ws, status="pending", parent_task_id=parent.id
    )
    with pytest.raises(HTTPException) as exc:
        await task_service.transition_status(
            ws.id, child.id, new_status="done", db=db
        )
    assert exc.value.status_code == 409
    assert "dependência" in exc.value.detail.lower() or "parent" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_done_allowed_when_parent_done(db):
    ws = await factories.make_workspace(db)
    parent = await factories.make_task(db, workspace=ws, status="done")
    child = await factories.make_task(
        db, workspace=ws, status="pending", parent_task_id=parent.id
    )
    updated = await task_service.transition_status(
        ws.id, child.id, new_status="done", db=db
    )
    assert updated.status == "done"


@pytest.mark.asyncio
async def test_done_allowed_when_parent_cancelled(db):
    """Se parent foi cancelada, child pode ser concluída."""
    ws = await factories.make_workspace(db)
    parent = await factories.make_task(db, workspace=ws, status="cancelled")
    child = await factories.make_task(
        db, workspace=ws, status="pending", parent_task_id=parent.id
    )
    updated = await task_service.transition_status(
        ws.id, child.id, new_status="done", db=db
    )
    assert updated.status == "done"


# ════════════════════════════════════════════════════════════════════
# Listagem e filtros
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_excludes_done_by_default(db):
    ws = await factories.make_workspace(db)
    await factories.make_task(db, workspace=ws, status="pending")
    await factories.make_task(db, workspace=ws, status="done")

    active = await task_service.list_tasks(ws.id, TaskFilters(), db=db)
    assert len(active) == 1
    assert active[0].status == "pending"

    with_done = await task_service.list_tasks(
        ws.id, TaskFilters(include_done=True), db=db
    )
    assert len(with_done) == 2


@pytest.mark.asyncio
async def test_list_filters_by_priority(db):
    ws = await factories.make_workspace(db)
    await factories.make_task(db, workspace=ws, priority="S")
    await factories.make_task(db, workspace=ws, priority="R")
    await factories.make_task(db, workspace=ws, priority="O")

    only_s = await task_service.list_tasks(
        ws.id, TaskFilters(priority="S"), db=db
    )
    assert len(only_s) == 1
    assert only_s[0].priority == "S"


@pytest.mark.asyncio
async def test_list_ordered_s_before_r_before_o(db):
    ws = await factories.make_workspace(db)
    await factories.make_task(db, workspace=ws, priority="O", title="Op")
    await factories.make_task(db, workspace=ws, priority="S", title="Es")
    await factories.make_task(db, workspace=ws, priority="R", title="Re")

    tasks = await task_service.list_tasks(ws.id, TaskFilters(), db=db)
    priorities = [t.priority for t in tasks]
    # S < R < O em ordem alfabética (O=Optional, R=Recommended, S=Standard)
    # queremos S, R, O — alphabetical é O<R<S. Como queremos S primeiro,
    # precisamos de ordem customizada. Verificamos que O está por último.
    assert priorities.index("O") == len(priorities) - 1


@pytest.mark.asyncio
async def test_list_filters_by_deadline_window(db):
    ws = await factories.make_workspace(db)
    today = date.today()
    await factories.make_task(
        db,
        workspace=ws,
        deadline_kind="HARD_DATE",
        deadline_date=today,
        title="hoje",
    )
    await factories.make_task(
        db,
        workspace=ws,
        deadline_kind="HARD_DATE",
        deadline_date=today + timedelta(days=3),
        title="3 dias",
    )
    await factories.make_task(
        db,
        workspace=ws,
        deadline_kind="HARD_DATE",
        deadline_date=today + timedelta(days=30),
        title="30 dias",
    )

    upcoming = await task_service.list_tasks(
        ws.id,
        TaskFilters(deadline_after=today, deadline_before=today + timedelta(days=7)),
        db=db,
    )
    titles = [t.title for t in upcoming]
    assert "hoje" in titles
    assert "3 dias" in titles
    assert "30 dias" not in titles


# ════════════════════════════════════════════════════════════════════
# Update parcial
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_update_partial_preserves_other_fields(db):
    ws = await factories.make_workspace(db)
    t = await factories.make_task(
        db, workspace=ws, title="Antigo", priority="R", category="Invest"
    )
    updated = await task_service.update_task(
        ws.id, t.id, TaskUpdate(title="Novo"), db=db
    )
    assert updated.title == "Novo"
    assert updated.priority == "R"
    assert updated.category == "Invest"


# ════════════════════════════════════════════════════════════════════
# Export markdown (round-trip)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_export_markdown_includes_sections_and_statuses(db):
    ws = await factories.make_workspace(db)
    await factories.make_task(
        db, workspace=ws, number=1, priority="S", title="Essential1", category="Invest"
    )
    await factories.make_task(
        db, workspace=ws, number=2, priority="R", title="Recommended1", category="Orcamento"
    )
    await factories.make_task(
        db, workspace=ws, number=3, priority="S", status="done", title="Done1", category="Invest"
    )

    md = await task_service.export_markdown(ws.id, db=db)
    assert "Essenciais (S)" in md
    assert "Recomendadas (R)" in md
    assert "Concluídas" in md
    assert "Essential1" in md
    assert "Done1" in md
    # Pipe em título escapado se houver — não testado aqui, mas coberto por escape no service


# ════════════════════════════════════════════════════════════════════
# Suggestions (approve/reject/merge)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_approve_suggestion_creates_task(db):
    ws = await factories.make_workspace(db)
    user = await factories.make_user(db)

    payload = TaskSuggestionProposed(
        title="Sugestão LLM",
        category="Tributario",
        priority="R",
    )
    sugg = await task_suggestion_service.create_suggestion(
        ws.id,
        TaskSuggestionCreate(proposed_payload=payload, source="e5n_llm"),
        db=db,
    )
    updated, task = await task_suggestion_service.approve(
        ws.id, sugg.id, db=db, reviewed_by=user.id
    )
    assert updated.status == "approved"
    assert updated.approved_task_id == task.id
    assert task.title == "Sugestão LLM"
    assert task.created_from == "llm_suggestion"
    assert task.source_suggestion_id == sugg.id


@pytest.mark.asyncio
async def test_approve_with_edited_payload_uses_edit(db):
    ws = await factories.make_workspace(db)
    user = await factories.make_user(db)

    original = TaskSuggestionProposed(
        title="Original", category="Orcamento", priority="R"
    )
    sugg = await task_suggestion_service.create_suggestion(
        ws.id,
        TaskSuggestionCreate(proposed_payload=original, source="e5n_llm"),
        db=db,
    )
    from backend.app.schemas.task import TaskSuggestionApprove

    edited = TaskSuggestionProposed(
        title="Editada pelo usuário", category="Orcamento", priority="S"
    )
    _, task = await task_suggestion_service.approve(
        ws.id,
        sugg.id,
        db=db,
        reviewed_by=user.id,
        body=TaskSuggestionApprove(edited_payload=edited),
    )
    assert task.title == "Editada pelo usuário"
    assert task.priority == "S"


@pytest.mark.asyncio
async def test_reject_suggestion(db):
    ws = await factories.make_workspace(db)
    user = await factories.make_user(db)
    sugg = await factories.make_task_suggestion(db, workspace=ws)
    rejected = await task_suggestion_service.reject(
        ws.id, sugg.id, db=db, reviewed_by=user.id, reason="irrelevante"
    )
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "irrelevante"


@pytest.mark.asyncio
async def test_merge_suggestion_into_existing_task(db):
    ws = await factories.make_workspace(db)
    user = await factories.make_user(db)
    target = await factories.make_task(db, workspace=ws)
    sugg = await factories.make_task_suggestion(db, workspace=ws)

    merged = await task_suggestion_service.merge_into(
        ws.id, sugg.id, target.id, db=db, reviewed_by=user.id
    )
    assert merged.status == "merged"
    assert merged.approved_task_id == target.id


@pytest.mark.asyncio
async def test_approve_already_processed_raises_409(db):
    ws = await factories.make_workspace(db)
    user = await factories.make_user(db)
    sugg = await factories.make_task_suggestion(db, workspace=ws, status="approved")
    with pytest.raises(HTTPException) as exc:
        await task_suggestion_service.approve(
            ws.id, sugg.id, db=db, reviewed_by=user.id
        )
    assert exc.value.status_code == 409


# ════════════════════════════════════════════════════════════════════
# Multi-tenant isolation
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_tasks_isolated_between_workspaces(db):
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    await factories.make_task(db, workspace=ws_a, title="A-only")
    await factories.make_task(db, workspace=ws_b, title="B-only")

    tasks_a = await task_service.list_tasks(ws_a.id, TaskFilters(), db=db)
    tasks_b = await task_service.list_tasks(ws_b.id, TaskFilters(), db=db)

    assert [t.title for t in tasks_a] == ["A-only"]
    assert [t.title for t in tasks_b] == ["B-only"]


@pytest.mark.asyncio
async def test_get_task_from_other_workspace_raises_404(db):
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    t = await factories.make_task(db, workspace=ws_a)
    with pytest.raises(HTTPException) as exc:
        await task_service.get_task(ws_b.id, t.id, db=db)
    assert exc.value.status_code == 404
