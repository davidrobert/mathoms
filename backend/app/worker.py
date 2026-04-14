"""Celery application — task queue for pipeline execution.

Start worker:
    celery -A backend.app.worker worker -l info -c 2
"""

from celery import Celery

from backend.app.core.config import settings

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
)

celery_app.autodiscover_tasks(["backend.app.tasks"])
