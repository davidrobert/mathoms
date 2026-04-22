"""Use cases do sub-agregado ``TaskSuggestion`` — testes puros."""

from __future__ import annotations

import pytest

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.task import (
    approve_task_suggestion,
    create_task_suggestion,
    list_task_suggestions,
    merge_suggestion_into_task,
    reject_task_suggestion,
)
from backend.app.application.task.create_task import create_task
from backend.app.schemas.dto.task import (
    TaskCreateCommand,
    TaskSuggestionApproveCommand,
    TaskSuggestionCreateCommand,
    TaskSuggestionProposed,
)
from backend.tests.fakes import (
    FakeTaskRepository,
    FakeTaskSuggestionRepository,
)


def _proposed(**overrides) -> TaskSuggestionProposed:
    base = dict(title="Revisar taxa PGBL", category="Invest", priority="R")
    base.update(overrides)
    return TaskSuggestionProposed(**base)


def _create_cmd(**overrides) -> TaskSuggestionCreateCommand:
    return TaskSuggestionCreateCommand(
        proposed_payload=_proposed(**overrides),
        source="e5n_llm",
    )


@pytest.mark.asyncio
async def test_create_suggestion_starts_pending():
    repo = FakeTaskSuggestionRepository()

    resp = await create_task_suggestion(
        _create_cmd(), workspace_id="ws-1", repo=repo
    )

    assert resp.status == "pending"
    assert resp.proposed_payload["title"] == "Revisar taxa PGBL"


@pytest.mark.asyncio
async def test_list_pending_orders_newest_first():
    repo = FakeTaskSuggestionRepository()
    first = await create_task_suggestion(
        _create_cmd(title="Primeira"), workspace_id="ws-1", repo=repo
    )
    second = await create_task_suggestion(
        _create_cmd(title="Segunda"), workspace_id="ws-1", repo=repo
    )

    # Força ordem cronológica no fake
    import datetime as _dt
    repo._suggestions[first.id].created_at = _dt.datetime(
        2026, 4, 1, tzinfo=_dt.timezone.utc
    )
    repo._suggestions[second.id].created_at = _dt.datetime(
        2026, 4, 15, tzinfo=_dt.timezone.utc
    )

    resp = await list_task_suggestions("ws-1", repo=repo)
    assert resp.total == 2
    assert resp.suggestions[0].id == second.id  # mais recente primeiro


@pytest.mark.asyncio
async def test_approve_materializes_task_and_marks_approved():
    sugg_repo = FakeTaskSuggestionRepository()
    task_repo = FakeTaskRepository()
    created = await create_task_suggestion(
        _create_cmd(), workspace_id="ws-1", repo=sugg_repo
    )

    sugg_resp, task_resp = await approve_task_suggestion(
        "ws-1",
        created.id,
        suggestion_repo=sugg_repo,
        task_repo=task_repo,
        reviewed_by="user-1",
    )

    assert sugg_resp.status == "approved"
    assert sugg_resp.approved_task_id == task_resp.id
    assert task_resp.created_from == "llm_suggestion"
    assert task_resp.source_suggestion_id == created.id


@pytest.mark.asyncio
async def test_approve_with_edited_payload_overrides():
    sugg_repo = FakeTaskSuggestionRepository()
    task_repo = FakeTaskRepository()
    created = await create_task_suggestion(
        _create_cmd(), workspace_id="ws-1", repo=sugg_repo
    )

    body = TaskSuggestionApproveCommand(
        edited_payload=_proposed(title="Editado pelo usuário")
    )
    _, task_resp = await approve_task_suggestion(
        "ws-1",
        created.id,
        suggestion_repo=sugg_repo,
        task_repo=task_repo,
        body=body,
    )
    assert task_resp.title == "Editado pelo usuário"


@pytest.mark.asyncio
async def test_approve_already_processed_raises_conflict():
    sugg_repo = FakeTaskSuggestionRepository()
    task_repo = FakeTaskRepository()
    created = await create_task_suggestion(
        _create_cmd(), workspace_id="ws-1", repo=sugg_repo
    )
    await approve_task_suggestion(
        "ws-1",
        created.id,
        suggestion_repo=sugg_repo,
        task_repo=task_repo,
    )

    with pytest.raises(ConflictError) as exc:
        await approve_task_suggestion(
            "ws-1",
            created.id,
            suggestion_repo=sugg_repo,
            task_repo=task_repo,
        )
    assert exc.value.code == "suggestion_not_pending"


@pytest.mark.asyncio
async def test_approve_missing_raises_not_found():
    sugg_repo = FakeTaskSuggestionRepository()
    task_repo = FakeTaskRepository()

    with pytest.raises(NotFoundError):
        await approve_task_suggestion(
            "ws-1",
            "missing",
            suggestion_repo=sugg_repo,
            task_repo=task_repo,
        )


@pytest.mark.asyncio
async def test_reject_records_reason():
    repo = FakeTaskSuggestionRepository()
    created = await create_task_suggestion(
        _create_cmd(), workspace_id="ws-1", repo=repo
    )

    resp = await reject_task_suggestion(
        "ws-1",
        created.id,
        repo=repo,
        reviewed_by="user-1",
        reason="Já está coberto pela Task #12",
    )
    assert resp.status == "rejected"
    assert resp.rejection_reason == "Já está coberto pela Task #12"


@pytest.mark.asyncio
async def test_merge_attaches_to_existing_task():
    sugg_repo = FakeTaskSuggestionRepository()
    task_repo = FakeTaskRepository()
    existing = await create_task(
        TaskCreateCommand(title="Já existe", category="Invest", priority="S"),
        workspace_id="ws-1",
        repo=task_repo,
    )
    sugg = await create_task_suggestion(
        _create_cmd(), workspace_id="ws-1", repo=sugg_repo
    )

    resp = await merge_suggestion_into_task(
        "ws-1",
        sugg.id,
        existing.id,
        suggestion_repo=sugg_repo,
        task_repo=task_repo,
    )
    assert resp.status == "merged"
    assert resp.approved_task_id == existing.id


@pytest.mark.asyncio
async def test_merge_rejects_unknown_target_task():
    sugg_repo = FakeTaskSuggestionRepository()
    task_repo = FakeTaskRepository()
    sugg = await create_task_suggestion(
        _create_cmd(), workspace_id="ws-1", repo=sugg_repo
    )

    with pytest.raises(NotFoundError) as exc:
        await merge_suggestion_into_task(
            "ws-1",
            sugg.id,
            "ghost-task",
            suggestion_repo=sugg_repo,
            task_repo=task_repo,
        )
    assert exc.value.code == "task_not_found"
