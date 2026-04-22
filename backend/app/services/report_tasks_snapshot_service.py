"""Snapshot imutável de tasks no relatório (ADR-074 §F8.3).

Ao gerar um `Report`, copia o estado atual de `tasks` para
`report.tasks_snapshot_json`. Relatórios ficam assim preservando a
"foto" do backlog naquele momento, mesmo que o DB mude depois.

A leitura do relatório (`GET /reports/{id}/tasks`):
  - Se `tasks_snapshot_json` estiver populado → retorna o snapshot.
  - Senão → fallback para o estado live (retrocompatível com relatórios
    pré-F8.3 que não tinham snapshot).

Formato do snapshot (estável — mudanças devem ser versionadas):

    {
      "version": 1,
      "captured_at": "2026-04-15T12:34:56Z",
      "total": 43,
      "counts_by_status": {"pending": 37, "done": 2, ...},
      "counts_by_priority": {"S": 10, "R": 28, "O": 5},
      "tasks": [
        {
          "number": 1, "title": "...", "category": "Invest",
          "priority": "S", "status": "pending", "ref": "D01",
          "deadline_kind": "MONTH", "deadline_label": "Abr/2026",
          "deadline_date": "2026-04-01"
        }, ...
      ]
    }
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

from backend.app.models.task import Task

SNAPSHOT_VERSION = 1


def _task_to_snapshot(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "number": task.number,
        "title": task.title,
        "description": task.description,
        "category": task.category,
        "priority": task.priority,
        "status": task.status,
        "ref": task.ref,
        "deadline_kind": task.deadline_kind,
        "deadline_date": task.deadline_date.isoformat() if task.deadline_date else None,
        "deadline_label": task.deadline_label,
        "parent_task_id": task.parent_task_id,
    }


def _serialize_tasks(tasks: list[Task]) -> dict[str, Any]:
    """Parte pura — recebe lista de Tasks e constrói o dict do snapshot.
    Compartilhada por `build_snapshot` (async) e `build_snapshot_sync`."""
    by_status = Counter(t.status for t in tasks)
    by_priority = Counter(t.priority for t in tasks)
    return {
        "version": SNAPSHOT_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "total": len(tasks),
        "counts_by_status": dict(by_status),
        "counts_by_priority": dict(by_priority),
        "tasks": [_task_to_snapshot(t) for t in tasks],
    }


def build_snapshot_sync(
    workspace_id: str,
    *,
    db: SyncSession,
) -> dict[str, Any]:
    """Versão síncrona de `build_snapshot` para uso dentro do Celery
    worker (`pipeline_task.py`), que opera sobre `SyncSessionLocal`.

    Mantém a mesma shape do snapshot → compatível com `get_report_snapshot`.
    """
    stmt = select(Task).where(Task.workspace_id == workspace_id).order_by(Task.number.asc())
    tasks = list(db.execute(stmt).scalars().all())
    return _serialize_tasks(tasks)


async def build_snapshot(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> dict[str, Any]:
    """Constrói o dict de snapshot a partir do estado atual do DB."""
    stmt = select(Task).where(Task.workspace_id == workspace_id).order_by(Task.number.asc())
    tasks = list((await db.execute(stmt)).scalars().all())
    return _serialize_tasks(tasks)


async def get_report_snapshot(
    workspace_id: str,
    report_id: str,
    *,
    db: AsyncSession,
) -> Optional[dict[str, Any]]:
    """Retorna o snapshot do relatório OU None se o relatório não tem snapshot
    (pré-F8.3). Caller decide fallback para estado live.

    Valida tenancy: `report.workspace_id == workspace_id`.
    """
    from backend.app.models.report import Report

    stmt = select(Report).where(Report.workspace_id == workspace_id, Report.id == report_id)
    report = (await db.execute(stmt)).scalar_one_or_none()
    if report is None:
        return None
    return report.tasks_snapshot_json


__all__ = [
    "SNAPSHOT_VERSION",
    "build_snapshot",
    "build_snapshot_sync",
    "get_report_snapshot",
]
