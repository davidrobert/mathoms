#!/usr/bin/env python3
"""dev/migrate_kanban_to_task.py — backfill ADR-153 M1 (kanban_items+report_notes → tasks+workspace_notes; idempotente)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import func, select  # noqa: E402

from backend.app.core.database import async_session  # noqa: E402
from backend.app.models.report_collab import KanbanItem, ReportNotes  # noqa: E402
from backend.app.models.task import Task  # noqa: E402
from backend.app.models.workspace import Workspace  # noqa: E402
from backend.app.models.workspace_note import WorkspaceNotes  # noqa: E402

logger = logging.getLogger("mathoms.migrator.kanban_to_task")

_PRIORIDADE_TO_URGENCY = {"alta": "alta", "media": "media", "baixa": "baixa"}
_COLUNA_TO_STATUS = {
    "a_fazer": "pending",
    "em_andamento": "in_progress",
    "concluido": "done",
}
_MIGRATED_NOTE_TITLE = "Notas migradas do relatório"


@dataclass(frozen=True)
class MigrationStats:
    workspace_id: str
    kanban_items_seen: int
    tasks_created: int
    tasks_skipped: int
    report_notes_seen: int
    workspace_notes_created: int
    workspace_notes_skipped: int


async def _next_task_number(session, workspace_id: str) -> int:
    """Próximo number livre no workspace (max+1, mínimo 1)."""
    result = await session.execute(
        select(func.coalesce(func.max(Task.number), 0)).where(Task.workspace_id == workspace_id)
    )
    return int(result.scalar() or 0) + 1


def _kanban_to_task(item: KanbanItem, *, workspace_id: str, number: int) -> Task:
    return Task(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        number=number,
        title=item.titulo,
        category=item.categoria or "Pipeline",
        priority=item.essencial or "O",
        urgency=_PRIORIDADE_TO_URGENCY.get(item.prioridade or ""),
        deadline_kind="HARD_DATE" if item.prazo else "UNSCHEDULED",
        deadline_date=item.prazo,
        status=_COLUNA_TO_STATUS.get(item.coluna, "pending"),
        board_column=item.coluna,
        board_order=item.ordem,
        origin_report_id=item.report_id,
        is_board_only=True,
        created_from="kanban_migration",
        source_suggestion_id=item.id,
        created_by=item.created_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _existing_kanban_origin_ids(session, workspace_id: str) -> set[str]:
    existing_q = await session.execute(
        select(Task.source_suggestion_id).where(
            Task.workspace_id == workspace_id,
            Task.created_from == "kanban_migration",
        )
    )
    return {row[0] for row in existing_q.all() if row[0]}


async def _list_kanban_items(session, workspace_id: str) -> list[KanbanItem]:
    q = await session.execute(
        select(KanbanItem)
        .where(KanbanItem.workspace_id == workspace_id)
        .order_by(KanbanItem.created_at.asc())
    )
    return list(q.scalars().all())


async def _migrate_kanban_for_workspace(
    session, workspace_id: str, *, dry_run: bool
) -> tuple[int, int, int]:
    items = await _list_kanban_items(session, workspace_id)
    seen, created, skipped = len(items), 0, 0
    if not items:
        return seen, created, skipped
    existing = await _existing_kanban_origin_ids(session, workspace_id)
    next_num = await _next_task_number(session, workspace_id)
    for item in items:
        if item.id in existing:
            skipped += 1
            continue
        if not dry_run:
            session.add(_kanban_to_task(item, workspace_id=workspace_id, number=next_num))
            await session.flush()
        next_num += 1
        created += 1
    return seen, created, skipped


def _concat_report_notes(notes: list[ReportNotes]) -> str:
    chunks: list[str] = []
    for note in notes:
        if not note.content.strip():
            continue
        chunks.append(f"## Relatório {note.report_id} — {note.created_at:%Y-%m-%d}")
        chunks.append(note.content.strip())
        chunks.append("")
    return "\n".join(chunks).strip()


async def _has_migrated_workspace_note(session, workspace_id: str) -> bool:
    existing_q = await session.execute(
        select(WorkspaceNotes).where(
            WorkspaceNotes.workspace_id == workspace_id,
            WorkspaceNotes.title == _MIGRATED_NOTE_TITLE,
        )
    )
    return existing_q.scalar_one_or_none() is not None


async def _list_report_notes(session, workspace_id: str) -> list[ReportNotes]:
    q = await session.execute(
        select(ReportNotes)
        .where(ReportNotes.workspace_id == workspace_id)
        .order_by(ReportNotes.created_at.asc())
    )
    return list(q.scalars().all())


def _build_workspace_note(workspace_id: str, content: str) -> WorkspaceNotes:
    return WorkspaceNotes(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        title=_MIGRATED_NOTE_TITLE,
        content=content,
        pinned=True,
    )


async def _migrate_notes_for_workspace(
    session, workspace_id: str, *, dry_run: bool
) -> tuple[int, int, int]:
    notes = await _list_report_notes(session, workspace_id)
    seen = len(notes)
    if seen == 0:
        return seen, 0, 0
    if await _has_migrated_workspace_note(session, workspace_id):
        return seen, 0, 1
    content = _concat_report_notes(notes)
    if not content:
        return seen, 0, 0
    if not dry_run:
        session.add(_build_workspace_note(workspace_id, content))
        await session.flush()
    return seen, 1, 0


async def _migrate_with_session(session, workspace_id: str, *, dry_run: bool) -> MigrationStats:
    kanban_seen, kanban_created, kanban_skipped = await _migrate_kanban_for_workspace(
        session, workspace_id, dry_run=dry_run
    )
    notes_seen, notes_created, notes_skipped = await _migrate_notes_for_workspace(
        session, workspace_id, dry_run=dry_run
    )
    if not dry_run:
        await session.commit()
    return MigrationStats(
        workspace_id=workspace_id,
        kanban_items_seen=kanban_seen,
        tasks_created=kanban_created,
        tasks_skipped=kanban_skipped,
        report_notes_seen=notes_seen,
        workspace_notes_created=notes_created,
        workspace_notes_skipped=notes_skipped,
    )


async def migrate_workspace(
    workspace_id: str,
    *,
    dry_run: bool,
    session=None,
    session_factory=None,
) -> MigrationStats:
    """Backfill ws (kanban→tasks + notes→workspace_notes); session pode ser injetada (pytest)."""
    if session is not None:
        return await _migrate_with_session(session, workspace_id, dry_run=dry_run)

    factory = session_factory or async_session
    async with factory() as new_session:
        return await _migrate_with_session(new_session, workspace_id, dry_run=dry_run)


async def _list_workspaces(session_factory=None) -> list[str]:
    factory = session_factory or async_session
    async with factory() as session:
        result = await session.execute(select(Workspace.id))
        return [row[0] for row in result.all()]


def _format_stats(stats: MigrationStats) -> str:
    return (
        f"workspace={stats.workspace_id} "
        f"kanban_seen={stats.kanban_items_seen} "
        f"tasks_created={stats.tasks_created} "
        f"tasks_skipped={stats.tasks_skipped} "
        f"notes_seen={stats.report_notes_seen} "
        f"notes_created={stats.workspace_notes_created} "
        f"notes_skipped={stats.workspace_notes_skipped}"
    )


async def _resolve_targets(workspace_id: Optional[str] = None, *, all_ws: bool) -> list[str]:
    if workspace_id and all_ws:
        raise ValueError("Use --workspace-id OU --all, não ambos.")
    if all_ws:
        return await _list_workspaces()
    if workspace_id:
        return [workspace_id]
    raise ValueError("Forneça --workspace-id <uuid> ou --all.")


async def _run(workspace_id: Optional[str] = None, *, all_ws: bool, dry_run: bool) -> int:
    try:
        targets = await _resolve_targets(workspace_id, all_ws=all_ws)
    except ValueError as exc:
        logger.error(str(exc))
        return 2
    if not targets:
        logger.warning("Nenhum workspace encontrado.")
        return 0
    for ws_id in targets:
        stats = await migrate_workspace(ws_id, dry_run=dry_run)
        logger.info(_format_stats(stats))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", type=str, default=None)
    parser.add_argument("--all", action="store_true", dest="all_ws")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return asyncio.run(_run(args.workspace_id, all_ws=args.all_ws, dry_run=args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
