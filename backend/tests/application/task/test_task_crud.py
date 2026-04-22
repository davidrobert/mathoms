"""Use cases de CRUD do agregado ``Task`` — testes puros (sem DB)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.application.task import (
    cancel_task,
    create_task,
    get_task,
    list_workspace_tasks,
    transition_task_status,
    update_task,
)
from backend.app.schemas.dto.task import (
    TaskCreateCommand,
    TaskFilters,
    TaskUpdateCommand,
)
from backend.tests.fakes import FakeTaskRepository


def _cmd(**overrides) -> TaskCreateCommand:
    base = dict(
        title="Revisar alocação",
        category="Invest",
        priority="S",
    )
    base.update(overrides)
    return TaskCreateCommand(**base)


@pytest.mark.asyncio
async def test_create_task_auto_assigns_number():
    repo = FakeTaskRepository()

    first = await create_task(_cmd(), workspace_id="ws-1", repo=repo)
    second = await create_task(
        _cmd(title="Comprar seguro", category="Seguros"),
        workspace_id="ws-1",
        repo=repo,
    )

    assert first.number == 1
    assert second.number == 2
    assert first.status == "pending"


@pytest.mark.asyncio
async def test_create_task_respects_explicit_number():
    repo = FakeTaskRepository()

    resp = await create_task(_cmd(number=42), workspace_id="ws-1", repo=repo)

    assert resp.number == 42


@pytest.mark.asyncio
async def test_create_task_rejects_invalid_category():
    repo = FakeTaskRepository()

    with pytest.raises(ValidationError) as exc:
        await create_task(
            _cmd(category="CategoriaInexistente"),
            workspace_id="ws-1",
            repo=repo,
        )
    assert exc.value.code == "invalid_category"


@pytest.mark.asyncio
async def test_create_task_rejects_invalid_parent():
    repo = FakeTaskRepository()

    with pytest.raises(ValidationError) as exc:
        await create_task(
            _cmd(parent_task_id="non-existent-id"),
            workspace_id="ws-1",
            repo=repo,
        )
    assert exc.value.code == "invalid_parent"


@pytest.mark.asyncio
async def test_get_task_raises_not_found():
    repo = FakeTaskRepository()

    with pytest.raises(NotFoundError) as exc:
        await get_task("ws-1", "missing-id", repo=repo)
    assert exc.value.code == "task_not_found"


@pytest.mark.asyncio
async def test_list_workspace_tasks_filters_and_sorts():
    repo = FakeTaskRepository()
    await create_task(_cmd(title="Opcional", priority="O"), workspace_id="ws-1", repo=repo)
    await create_task(_cmd(title="Essencial", priority="S"), workspace_id="ws-1", repo=repo)
    await create_task(_cmd(title="Recomendada", priority="R"), workspace_id="ws-1", repo=repo)

    resp = await list_workspace_tasks("ws-1", TaskFilters(), repo=repo)

    # Ordem S → R → O
    assert [t.priority for t in resp.tasks] == ["S", "R", "O"]
    assert resp.total == 3


@pytest.mark.asyncio
async def test_list_workspace_tasks_excludes_done_by_default():
    repo = FakeTaskRepository()
    done = await create_task(_cmd(), workspace_id="ws-1", repo=repo)
    await transition_task_status("ws-1", done.id, new_status="done", repo=repo)
    await create_task(_cmd(title="Ativa", category="Orcamento"), workspace_id="ws-1", repo=repo)

    resp = await list_workspace_tasks("ws-1", TaskFilters(), repo=repo)
    assert resp.total == 1
    assert resp.tasks[0].title == "Ativa"

    resp_with_done = await list_workspace_tasks("ws-1", TaskFilters(include_done=True), repo=repo)
    assert resp_with_done.total == 2


@pytest.mark.asyncio
async def test_update_task_partial_fields():
    repo = FakeTaskRepository()
    created = await create_task(_cmd(), workspace_id="ws-1", repo=repo)

    resp = await update_task(
        TaskUpdateCommand(title="Novo título", priority="R"),
        workspace_id="ws-1",
        task_id=created.id,
        repo=repo,
    )
    assert resp.title == "Novo título"
    assert resp.priority == "R"
    assert resp.category == "Invest"  # preservado


@pytest.mark.asyncio
async def test_update_task_rejects_invalid_category():
    repo = FakeTaskRepository()
    created = await create_task(_cmd(), workspace_id="ws-1", repo=repo)

    with pytest.raises(ValidationError):
        await update_task(
            TaskUpdateCommand(category="NaoExiste"),
            workspace_id="ws-1",
            task_id=created.id,
            repo=repo,
        )


@pytest.mark.asyncio
async def test_update_task_with_status_delegates_to_transition():
    repo = FakeTaskRepository()
    created = await create_task(_cmd(), workspace_id="ws-1", repo=repo)

    resp = await update_task(
        TaskUpdateCommand(status="done"),
        workspace_id="ws-1",
        task_id=created.id,
        repo=repo,
    )
    assert resp.status == "done"
    assert resp.completed_at is not None


@pytest.mark.asyncio
async def test_transition_rejects_invalid_status():
    repo = FakeTaskRepository()
    created = await create_task(_cmd(), workspace_id="ws-1", repo=repo)

    with pytest.raises(ValidationError) as exc:
        await transition_task_status("ws-1", created.id, new_status="foo", repo=repo)
    assert exc.value.code == "invalid_status"


@pytest.mark.asyncio
async def test_transition_rejects_disallowed_path():
    repo = FakeTaskRepository()
    created = await create_task(_cmd(), workspace_id="ws-1", repo=repo)
    # pending não vai direto para blocked-cancel paths inválidos
    await transition_task_status("ws-1", created.id, new_status="done", repo=repo)
    # done → blocked é inválido (done aceita apenas pending/in_progress)
    with pytest.raises(ConflictError) as exc:
        await transition_task_status("ws-1", created.id, new_status="blocked", repo=repo)
    assert exc.value.code == "invalid_transition"


@pytest.mark.asyncio
async def test_transition_done_blocked_by_pending_parent():
    repo = FakeTaskRepository()
    parent = await create_task(_cmd(title="Parent"), workspace_id="ws-1", repo=repo)
    child = await create_task(
        _cmd(title="Child", parent_task_id=parent.id),
        workspace_id="ws-1",
        repo=repo,
    )

    with pytest.raises(ConflictError) as exc:
        await transition_task_status("ws-1", child.id, new_status="done", repo=repo)
    assert exc.value.code == "parent_not_done"


@pytest.mark.asyncio
async def test_transition_done_succeeds_when_parent_done():
    repo = FakeTaskRepository()
    parent = await create_task(_cmd(title="Parent"), workspace_id="ws-1", repo=repo)
    child = await create_task(
        _cmd(title="Child", parent_task_id=parent.id),
        workspace_id="ws-1",
        repo=repo,
    )
    await transition_task_status("ws-1", parent.id, new_status="done", repo=repo)

    resp = await transition_task_status("ws-1", child.id, new_status="done", repo=repo)
    assert resp.status == "done"


@pytest.mark.asyncio
async def test_transition_reopen_from_done_zeroes_timestamps():
    repo = FakeTaskRepository()
    created = await create_task(_cmd(), workspace_id="ws-1", repo=repo)
    await transition_task_status("ws-1", created.id, new_status="done", repo=repo)

    resp = await transition_task_status("ws-1", created.id, new_status="pending", repo=repo)
    assert resp.status == "pending"
    assert resp.completed_at is None


@pytest.mark.asyncio
async def test_cancel_task_soft_deletes():
    repo = FakeTaskRepository()
    created = await create_task(_cmd(), workspace_id="ws-1", repo=repo)

    await cancel_task("ws-1", created.id, repo=repo)
    resp = await get_task("ws-1", created.id, repo=repo)
    assert resp.status == "cancelled"
    assert resp.cancelled_at is not None


@pytest.mark.asyncio
async def test_workspace_isolation():
    repo = FakeTaskRepository()
    await create_task(_cmd(), workspace_id="ws-A", repo=repo)
    await create_task(_cmd(), workspace_id="ws-B", repo=repo)

    a = await list_workspace_tasks("ws-A", TaskFilters(), repo=repo)
    b = await list_workspace_tasks("ws-B", TaskFilters(), repo=repo)
    assert a.total == 1 and b.total == 1
    assert a.tasks[0].workspace_id == "ws-A"


@pytest.mark.asyncio
async def test_list_filters_by_deadline():
    repo = FakeTaskRepository()
    today = date.today()
    await create_task(
        _cmd(title="Perto", deadline_kind="HARD_DATE", deadline_date=today + timedelta(days=2)),
        workspace_id="ws-1",
        repo=repo,
    )
    await create_task(
        _cmd(title="Longe", deadline_kind="HARD_DATE", deadline_date=today + timedelta(days=30)),
        workspace_id="ws-1",
        repo=repo,
    )

    resp = await list_workspace_tasks(
        "ws-1",
        TaskFilters(
            deadline_after=today,
            deadline_before=today + timedelta(days=7),
        ),
        repo=repo,
    )
    assert resp.total == 1
    assert resp.tasks[0].title == "Perto"
