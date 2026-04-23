"""Use case: tasks do relatório — snapshot imutável ou fallback live (ADR-074)."""

from __future__ import annotations

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.report._common import fetch_report
from backend.app.schemas.task import TaskFilters, TaskResponse
from backend.app.services import report_tasks_snapshot_service, task_service


async def get_report_tasks(workspace_id: str, report_id: str, *, db: AsyncSession) -> JSONResponse:
    snapshot = await report_tasks_snapshot_service.get_report_snapshot(
        workspace_id, report_id, db=db
    )
    if snapshot is not None:
        return JSONResponse(content={"is_live_fallback": False, **snapshot})

    # Fallback live: valida relatório antes de vazar tasks do workspace.
    await fetch_report(workspace_id, report_id, db=db)

    live_tasks = await task_service.list_tasks(
        workspace_id,
        TaskFilters(include_done=True, include_cancelled=True),
        db=db,
    )
    return JSONResponse(
        content={
            "is_live_fallback": True,
            "version": 1,
            "captured_at": None,
            "total": len(live_tasks),
            "counts_by_status": {},
            "counts_by_priority": {},
            "tasks": [TaskResponse.model_validate(t).model_dump(mode="json") for t in live_tasks],
        }
    )
