"""Testes unitários dos 3 repos do agregado Task (com DB real).

Cobrem:

- ``TaskRepository``:
  - ``list`` com TaskFilters (status, priority, category, deadline,
    goal, assigned); default oculta done/cancelled; include_* override.
  - ``list_all`` inclui done/cancelled (usado no export MD).
  - Ordenação S→R→O + deadline asc + number asc.
  - Isolamento multi-tenant (R13).
  - ``get_by_id``, ``get_by_number``, ``list_by_parent``, ``next_number``.
  - ``add`` com flush + ``delete``.
- ``TaskAttachmentRepository``:
  - ``list_by_task`` ordena DESC por ``created_at``.
  - Cross-tenant + cross-task safety.
  - ``add`` + ``delete``.
- ``TaskSuggestionRepository``:
  - ``list_by_status`` com default ``pending`` e ``status=None``.
  - Tenant isolation.
  - ``add`` + ``save`` (idempotente).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.task import Task, TaskAttachment, TaskSuggestion
from backend.app.models.workspace import Workspace
from backend.app.repositories.task_attachment_repository import (
    TaskAttachmentRepository,
)
from backend.app.repositories.task_repository import TaskRepository
from backend.app.repositories.task_suggestion_repository import (
    TaskSuggestionRepository,
)
from backend.app.schemas.dto.task import TaskFilters
from backend.tests.factories.builders import (
    make_task,
    make_task_suggestion,
    make_workspace,
)


@pytest_asyncio.fixture
async def two_workspaces(db: AsyncSession) -> tuple[Workspace, Workspace]:
    ws_a = await make_workspace(db, name="WS A")
    ws_b = await make_workspace(db, name="WS B")
    await db.commit()
    return ws_a, ws_b


# ---------------------------------------------------------------------------
# TaskRepository.list — filtros + ordenação
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_default_excludes_done_and_cancelled(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_task(db, workspace=ws_a, status="pending", title="T1")
    await make_task(db, workspace=ws_a, status="done", title="T2")
    await make_task(db, workspace=ws_a, status="cancelled", title="T3")
    await make_task(db, workspace=ws_a, status="in_progress", title="T4")
    await db.commit()

    repo = TaskRepository(db)
    tasks = await repo.list(ws_a.id, TaskFilters())

    assert {t.title for t in tasks} == {"T1", "T4"}


@pytest.mark.asyncio
async def test_list_include_done_and_cancelled(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_task(db, workspace=ws_a, status="pending", title="T1")
    await make_task(db, workspace=ws_a, status="done", title="T2")
    await make_task(db, workspace=ws_a, status="cancelled", title="T3")
    await db.commit()

    repo = TaskRepository(db)
    tasks = await repo.list(ws_a.id, TaskFilters(include_done=True, include_cancelled=True))

    assert {t.title for t in tasks} == {"T1", "T2", "T3"}


@pytest.mark.asyncio
async def test_list_filter_by_explicit_status(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_task(db, workspace=ws_a, status="pending", title="P1")
    await make_task(db, workspace=ws_a, status="blocked", title="B1")
    await make_task(db, workspace=ws_a, status="done", title="D1")
    await db.commit()

    repo = TaskRepository(db)
    tasks = await repo.list(ws_a.id, TaskFilters(status="blocked"))

    assert {t.title for t in tasks} == {"B1"}


@pytest.mark.asyncio
async def test_list_filter_by_priority_and_category(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_task(db, workspace=ws_a, priority="S", category="Invest", title="SI")
    await make_task(db, workspace=ws_a, priority="R", category="Invest", title="RI")
    await make_task(db, workspace=ws_a, priority="S", category="Orcamento", title="SO")
    await db.commit()

    repo = TaskRepository(db)
    tasks = await repo.list(ws_a.id, TaskFilters(priority="S", category="Invest"))

    assert {t.title for t in tasks} == {"SI"}


@pytest.mark.asyncio
async def test_list_filter_by_deadline_range(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_task(
        db,
        workspace=ws_a,
        deadline_kind="HARD_DATE",
        deadline_date=date(2026, 3, 15),
        title="Mar",
    )
    await make_task(
        db,
        workspace=ws_a,
        deadline_kind="HARD_DATE",
        deadline_date=date(2026, 5, 15),
        title="Mai",
    )
    await make_task(
        db,
        workspace=ws_a,
        deadline_kind="HARD_DATE",
        deadline_date=date(2026, 7, 15),
        title="Jul",
    )
    await db.commit()

    repo = TaskRepository(db)
    tasks = await repo.list(
        ws_a.id,
        TaskFilters(
            deadline_after=date(2026, 4, 1),
            deadline_before=date(2026, 6, 30),
        ),
    )

    assert {t.title for t in tasks} == {"Mai"}


@pytest.mark.asyncio
async def test_list_ordering_priority_s_before_r_before_o(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_task(db, workspace=ws_a, priority="O", title="Op", number=1)
    await make_task(db, workspace=ws_a, priority="S", title="St", number=2)
    await make_task(db, workspace=ws_a, priority="R", title="Re", number=3)
    await db.commit()

    repo = TaskRepository(db)
    tasks = await repo.list(ws_a.id, TaskFilters())

    assert [t.title for t in tasks] == ["St", "Re", "Op"]


@pytest.mark.asyncio
async def test_list_ordering_deadline_asc_nulls_last(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_task(
        db,
        workspace=ws_a,
        priority="R",
        deadline_kind="UNSCHEDULED",
        deadline_date=None,
        title="NoDate",
        number=1,
    )
    await make_task(
        db,
        workspace=ws_a,
        priority="R",
        deadline_kind="HARD_DATE",
        deadline_date=date(2026, 5, 1),
        title="Early",
        number=2,
    )
    await make_task(
        db,
        workspace=ws_a,
        priority="R",
        deadline_kind="HARD_DATE",
        deadline_date=date(2026, 7, 1),
        title="Late",
        number=3,
    )
    await db.commit()

    repo = TaskRepository(db)
    tasks = await repo.list(ws_a.id, TaskFilters())

    # Com datas antes das sem-data (asc); desempate por number.
    assert [t.title for t in tasks] == ["Early", "Late", "NoDate"]


@pytest.mark.asyncio
async def test_list_is_workspace_isolated(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces

    await make_task(db, workspace=ws_a, title="A1")
    await make_task(db, workspace=ws_b, title="B1")
    await db.commit()

    repo = TaskRepository(db)
    assert {t.title for t in await repo.list(ws_a.id, TaskFilters())} == {"A1"}
    assert {t.title for t in await repo.list(ws_b.id, TaskFilters())} == {"B1"}


# ---------------------------------------------------------------------------
# TaskRepository — get_by_id / get_by_number / list_by_parent / next_number
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_id_scoped_to_workspace(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces
    task = await make_task(db, workspace=ws_a)
    await db.commit()

    repo = TaskRepository(db)
    assert (await repo.get_by_id(ws_a.id, task.id)) is not None
    assert (await repo.get_by_id(ws_b.id, task.id)) is None
    assert (await repo.get_by_id(ws_a.id, "nonexistent")) is None


@pytest.mark.asyncio
async def test_get_by_number_scoped(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces
    await make_task(db, workspace=ws_a, number=7, title="N7A")
    await make_task(db, workspace=ws_b, number=7, title="N7B")
    await db.commit()

    repo = TaskRepository(db)

    task_a = await repo.get_by_number(ws_a.id, 7)
    task_b = await repo.get_by_number(ws_b.id, 7)

    assert task_a is not None and task_a.title == "N7A"
    assert task_b is not None and task_b.title == "N7B"
    # Número inexistente.
    assert (await repo.get_by_number(ws_a.id, 999)) is None


@pytest.mark.asyncio
async def test_list_by_parent(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    parent = await make_task(db, workspace=ws_a, title="Parent", number=1)
    await make_task(db, workspace=ws_a, title="Child 1", number=2, parent_task_id=parent.id)
    await make_task(db, workspace=ws_a, title="Child 2", number=3, parent_task_id=parent.id)
    await make_task(db, workspace=ws_a, title="Orphan", number=4)
    await db.commit()

    repo = TaskRepository(db)
    children = await repo.list_by_parent(ws_a.id, parent.id)

    assert [c.title for c in children] == ["Child 1", "Child 2"]


@pytest.mark.asyncio
async def test_next_number_empty_workspace(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    repo = TaskRepository(db)

    assert (await repo.next_number(ws_a.id)) == 1


@pytest.mark.asyncio
async def test_next_number_increments_max(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_task(db, workspace=ws_a, number=1)
    await make_task(db, workspace=ws_a, number=5)
    await make_task(db, workspace=ws_a, number=3)
    await db.commit()

    repo = TaskRepository(db)
    assert (await repo.next_number(ws_a.id)) == 6


@pytest.mark.asyncio
async def test_next_number_per_workspace(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces

    await make_task(db, workspace=ws_a, number=42)
    await db.commit()

    repo = TaskRepository(db)
    assert (await repo.next_number(ws_a.id)) == 43
    assert (await repo.next_number(ws_b.id)) == 1


@pytest.mark.asyncio
async def test_list_all_includes_done_cancelled(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_task(db, workspace=ws_a, status="pending", title="P", number=1)
    await make_task(db, workspace=ws_a, status="done", title="D", number=2)
    await make_task(db, workspace=ws_a, status="cancelled", title="C", number=3)
    await db.commit()

    repo = TaskRepository(db)
    all_tasks = await repo.list_all(ws_a.id)

    assert [t.number for t in all_tasks] == [1, 2, 3]
    assert {t.title for t in all_tasks} == {"P", "D", "C"}


# ---------------------------------------------------------------------------
# TaskRepository — add + delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_flushes_and_assigns_id(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    task = Task(
        workspace_id=ws_a.id,
        number=10,
        title="New",
        category="Invest",
        priority="R",
        deadline_kind="UNSCHEDULED",
        status="pending",
    )
    repo = TaskRepository(db)
    returned = await repo.add(task)

    assert returned is task
    assert task.id is not None
    await db.commit()


@pytest.mark.asyncio
async def test_delete_removes_row(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    task = await make_task(db, workspace=ws_a)
    await db.commit()

    repo = TaskRepository(db)
    await repo.delete(task)
    await db.commit()

    assert (await repo.get_by_id(ws_a.id, task.id)) is None


# ---------------------------------------------------------------------------
# TaskAttachmentRepository
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attachment_list_by_task_ordered_desc(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    task = await make_task(db, workspace=ws_a)

    att1 = TaskAttachment(
        task_id=task.id,
        workspace_id=ws_a.id,
        storage_path="p1",
        original_filename="1.pdf",
    )
    att2 = TaskAttachment(
        task_id=task.id,
        workspace_id=ws_a.id,
        storage_path="p2",
        original_filename="2.pdf",
    )
    repo = TaskAttachmentRepository(db)
    await repo.add(att1)
    await repo.add(att2)
    # Força ordem temporal explícita
    att1.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    att2.created_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    await db.commit()

    items = await repo.list_by_task(ws_a.id, task.id)

    assert [a.original_filename for a in items] == ["2.pdf", "1.pdf"]


@pytest.mark.asyncio
async def test_attachment_get_by_id_workspace_scoped(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces
    task = await make_task(db, workspace=ws_a)

    att = TaskAttachment(
        task_id=task.id,
        workspace_id=ws_a.id,
        storage_path="p1",
        original_filename="x.pdf",
    )
    repo = TaskAttachmentRepository(db)
    await repo.add(att)
    await db.commit()

    assert (await repo.get_by_id(ws_a.id, att.id)) is not None
    # Cross-tenant safety.
    assert (await repo.get_by_id(ws_b.id, att.id)) is None


@pytest.mark.asyncio
async def test_attachment_delete(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    task = await make_task(db, workspace=ws_a)

    att = TaskAttachment(
        task_id=task.id,
        workspace_id=ws_a.id,
        storage_path="p1",
        original_filename="x.pdf",
    )
    repo = TaskAttachmentRepository(db)
    await repo.add(att)
    await db.commit()

    await repo.delete(att)
    await db.commit()

    assert (await repo.get_by_id(ws_a.id, att.id)) is None


# ---------------------------------------------------------------------------
# TaskSuggestionRepository
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suggestion_list_default_pending(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    p = await make_task_suggestion(db, workspace=ws_a, status="pending")
    await make_task_suggestion(db, workspace=ws_a, status="rejected")
    await make_task_suggestion(db, workspace=ws_a, status="approved")
    await db.commit()

    repo = TaskSuggestionRepository(db)
    pending = await repo.list_by_status(ws_a.id)

    assert [s.id for s in pending] == [p.id]


@pytest.mark.asyncio
async def test_suggestion_list_all_when_status_none(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces

    await make_task_suggestion(db, workspace=ws_a, status="pending")
    await make_task_suggestion(db, workspace=ws_a, status="rejected")
    await make_task_suggestion(db, workspace=ws_a, status="merged")
    await db.commit()

    repo = TaskSuggestionRepository(db)
    all_ = await repo.list_by_status(ws_a.id, status=None)

    assert len(all_) == 3


@pytest.mark.asyncio
async def test_suggestion_is_workspace_isolated(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces
    await make_task_suggestion(db, workspace=ws_a, status="pending")
    await db.commit()

    repo = TaskSuggestionRepository(db)
    # ws_b não tem sugestões — isolamento multi-tenant.
    assert (await repo.list_by_status(ws_b.id)) == []


@pytest.mark.asyncio
async def test_suggestion_save_after_mutation(db: AsyncSession, two_workspaces):
    ws_a, _ = two_workspaces
    sugg = await make_task_suggestion(db, workspace=ws_a, status="pending")
    await db.commit()

    repo = TaskSuggestionRepository(db)
    sugg.status = "approved"
    sugg.reviewed_by = "user-1"
    await repo.save(sugg)
    await db.commit()

    re_read = await repo.get_by_id(ws_a.id, sugg.id)
    assert re_read is not None
    assert re_read.status == "approved"
    assert re_read.reviewed_by == "user-1"
