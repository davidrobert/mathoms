"""Tarefas periódicas Celery Beat — ADR-074 §F8.4.

Configura:
- `scan_all_deadlines`: varre todos os workspaces ativos e cria
  notificações de prazo para tasks com deadline ≤7 dias. Roda
  diariamente via beat schedule.

Start beat:
    celery -A backend.app.worker beat -l info

O schedule é configurado em `worker.py:celery_app.conf.beat_schedule`.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.models.workspace import Workspace
from backend.app.services.task_notification_service import (
    scan_and_create_notifications,
)
from backend.app.worker import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(name="fin.scan_all_deadlines", bind=True, max_retries=1)
def scan_all_deadlines(self) -> dict[str, int]:
    """Varre TODOS os workspaces e dispara `scan_and_create_notifications`
    para cada um. Idempotente (dedup por title no notification).

    Retorna contadores agregados:
        {"workspaces_scanned": N, "total_created": M, "total_skipped": S}
    """
    import asyncio

    total_created = 0
    total_skipped = 0
    ws_count = 0

    # sync session — beat tasks rodam fora do event loop async
    with SyncSessionLocal() as db:
        # tenancy: global — admin job que varre todos os workspaces
        ws_ids = [
            row[0]
            for row in db.execute(select(Workspace.id)).fetchall()
        ]

    for ws_id in ws_ids:
        try:
            stats = asyncio.run(_scan_one(ws_id))
            total_created += stats.get("created", 0)
            total_skipped += stats.get("skipped_existing", 0)
            ws_count += 1
        except Exception as exc:  # noqa: BLE001 — best-effort per workspace
            logger.warning(
                "scan_all_deadlines: workspace %s falhou: %s",
                ws_id,
                exc,
            )

    result = {
        "workspaces_scanned": ws_count,
        "total_created": total_created,
        "total_skipped": total_skipped,
    }
    logger.info("scan_all_deadlines: %s", result)
    return result


async def _scan_one(workspace_id: str) -> dict[str, int]:
    """Wrapper async para rodar o service (que usa AsyncSession)."""
    from backend.app.core.database import async_session as AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        stats = await scan_and_create_notifications(workspace_id, db=db)
        await db.commit()
    return stats
