"""Celery application — task queue for pipeline execution.

Start worker:
    celery -A backend.app.worker worker -l info -c 2
"""

import os
import sys
from pathlib import Path

from celery import Celery

from backend.app.core.config import settings

# BUG-002 fix: ensure project root is on sys.path so that `import pipeline`
# works inside the Celery worker process (fork pool doesn't inherit sys.path).
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# scripts.pipeline_common needs MATHOMS_WORKSPACE_ROOT; per-run tasks may override to tenant.
os.environ.setdefault("MATHOMS_WORKSPACE_ROOT", _project_root)

celery_app = Celery("fin")

celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_concurrency=2,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    # BUG-001 fix: explicit include instead of autodiscover_tasks.
    # autodiscover_tasks looks for a module named `tasks.py` inside the package,
    # but our task file is `pipeline_task.py`.
    include=[
        "backend.app.tasks.pipeline_task",
        "backend.app.tasks.periodic_tasks",
    ],
    # F8.4 / ADR-074 — beat schedule para tarefas periódicas.
    # Start beat: celery -A backend.app.worker beat -l info
    beat_schedule={
        "scan-deadlines-daily": {
            "task": "fin.scan_all_deadlines",
            "schedule": 86400.0,  # diário (24h em segundos)
        },
    },
)
