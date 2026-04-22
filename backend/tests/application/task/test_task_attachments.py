"""Use cases do sub-agregado ``TaskAttachment`` — testes puros."""

from __future__ import annotations

import pytest

from backend.app.application.base.errors import NotFoundError
from backend.app.application.task import (
    create_task,
    delete_task_attachment,
    list_task_attachments,
)
from backend.app.models.task import TaskAttachment
from backend.app.schemas.dto.task import TaskCreateCommand
from backend.tests.fakes import (
    FakeTaskAttachmentRepository,
    FakeTaskRepository,
)


def _attachment(task_id: str, workspace_id: str = "ws-1", **overrides) -> TaskAttachment:
    defaults = dict(
        task_id=task_id,
        workspace_id=workspace_id,
        storage_path=f"task_attachments/{task_id}/nota.pdf",
        original_filename="nota.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        uploaded_by=None,
    )
    defaults.update(overrides)
    return TaskAttachment(**defaults)


@pytest.mark.asyncio
async def test_list_attachments_requires_task():
    task_repo = FakeTaskRepository()
    attachment_repo = FakeTaskAttachmentRepository()

    with pytest.raises(NotFoundError) as exc:
        await list_task_attachments(
            "ws-1",
            "ghost-task",
            task_repo=task_repo,
            attachment_repo=attachment_repo,
        )
    assert exc.value.code == "task_not_found"


@pytest.mark.asyncio
async def test_list_attachments_returns_only_matches():
    task_repo = FakeTaskRepository()
    attachment_repo = FakeTaskAttachmentRepository()
    task = await create_task(
        TaskCreateCommand(title="Qualquer", category="Invest", priority="S"),
        workspace_id="ws-1",
        repo=task_repo,
    )
    await attachment_repo.add(_attachment(task.id))
    await attachment_repo.add(_attachment("outro-task-id"))

    resp = await list_task_attachments(
        "ws-1",
        task.id,
        task_repo=task_repo,
        attachment_repo=attachment_repo,
    )
    assert resp.total == 1
    assert resp.attachments[0].task_id == task.id


@pytest.mark.asyncio
async def test_delete_attachment_strips_row():
    repo = FakeTaskAttachmentRepository()
    att = await repo.add(_attachment("task-1"))

    returned = await delete_task_attachment("ws-1", "task-1", att.id, repo=repo)
    assert returned.id == att.id
    remaining = await repo.list_by_task("ws-1", "task-1")
    assert remaining == []


@pytest.mark.asyncio
async def test_delete_attachment_not_found():
    repo = FakeTaskAttachmentRepository()

    with pytest.raises(NotFoundError) as exc:
        await delete_task_attachment("ws-1", "task-1", "ghost", repo=repo)
    assert exc.value.code == "attachment_not_found"


@pytest.mark.asyncio
async def test_delete_attachment_task_mismatch():
    repo = FakeTaskAttachmentRepository()
    att = await repo.add(_attachment("task-1"))

    with pytest.raises(NotFoundError) as exc:
        await delete_task_attachment("ws-1", "task-DIFFERENT", att.id, repo=repo)
    assert exc.value.code == "attachment_task_mismatch"
