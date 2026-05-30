"""Celery application — task queue for pipeline execution.

Start worker:
    celery -A backend.app.worker worker -l info -c 2
"""

import sys
from pathlib import Path

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging
from backend.app.core.otel import instrument_celery, setup_otel

# BUG-002 fix: ensure project root is on sys.path so that `import pipeline`
# works inside the Celery worker process (fork pool doesn't inherit sys.path).
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

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
        "backend.app.tasks.lgpd_export",
        "backend.app.tasks.categorization_apply",
        # ADR-239 D5 (A18 L3 P1+P2) — FIPE refresh assíncrono via BrasilAPI.
        "backend.app.tasks.fipe_refresh",
    ],
    # F8.4 / ADR-074 — beat schedule para tarefas periódicas.
    # Start beat: celery -A backend.app.worker beat -l info
    beat_schedule={
        "scan-deadlines-daily": {
            "task": "fin.scan_all_deadlines",
            "schedule": 86400.0,  # diário (24h em segundos)
        },
        # LGPD self-service — expira tar.gz de exports passados do prazo
        # de download (default 7d). Roda a cada 6h para reduzir janela de
        # acesso ao arquivo já vencido.
        "lgpd-expire-data-exports": {
            "task": "fin.lgpd.expire_data_exports",
            "schedule": 21600.0,  # 6h
        },
        # LGPD Art. 18, VI — finaliza hard-delete de users marcados >30d
        # (DELETION_GRACE_DAYS em periodic_tasks).
        "lgpd-process-user-deletions": {
            "task": "fin.lgpd.process_user_deletions",
            "schedule": 86400.0,  # diário
        },
        # LGPD Art. 37 / ADR-275 D5 — purga audit de leitura >365d (retenção).
        # Audit de mutação (Art.16) sobrevive — filtro é READ_ACCESS_ACTIONS.
        "lgpd-purge-expired-audit-logs": {
            "task": "fin.lgpd.purge_expired_audit_logs",
            "schedule": 86400.0,  # diário
        },
        # ADR-172 (W2-T04) — detector de runs travados.
        "detect-stuck-runs": {
            "task": "fin.detect_stuck_runs",
            "schedule": 300.0,  # 5min
        },
        # ADR-239 D5 (A18 L3 P2) — refresh anual de FIPE em 15/Jan às 03h UTC
        # (todos vehicles ativos). Janeiro é alinhado com IRPF do exercício
        # seguinte — base fiscal para cap rate líquido de veículos (Dezembro/<ano-1>).
        "fipe-refresh-annual": {
            "task": "fin.fipe.refresh_all_annual",
            "schedule": crontab(month_of_year=1, day_of_month=15, hour=3, minute=0),
        },
    },
)


@worker_process_init.connect
def _init_worker_observability(**_: object) -> None:
    """Set up JSON logging + OTel in each Celery worker process (fork-safe)."""
    setup_logging()
    setup_otel(service_name="mathoms-worker")
    instrument_celery()
