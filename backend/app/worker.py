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
from backend.app.core.logging import get_logger, setup_logging
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
        # ADR-171 — re-encrypt batch durante janela de rotação Fernet (manual).
        "backend.app.tasks.rotate_fernet_secrets",
        # A33.l5 (ADR-307 F2) — drift nightly do extract_with_llm.
        "backend.app.tasks.detect_extract_llm_drift",
        # A33.l6 (W6-T05, ADR-212) — prune diário de pipeline_artifacts.
        "backend.app.tasks.prune_artifacts",
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
        # `expires` medido no co-design A40.l27: não há `task_routes`, então estas tasks
        # competem com `pipeline.run` (`task_time_limit=3600`) numa fila só, com
        # `worker_concurrency=2`. Dois runs longos famintam o reaper por até ~1h, e sem
        # `expires` o beat acumula N cópias que rodam em sequência quando um slot libera —
        # idempotentes, mas poluindo fila e log. Menor que o período: cópia velha morre.
        "detect-stuck-runs": {
            "task": "fin.detect_stuck_runs",
            "schedule": 300.0,  # 5min
            "options": {"expires": 240},
        },
        # A40.l27 (ADR-359 §Deferimentos) — colhe run pré-dispatch sem dono. Mesmo
        # período do detector acima; detecção worst-case = 300s + threshold (2min) — e
        # ILIMITADA sob fila funda pelo mesmo motivo acima, o que o runbook declara.
        "detect-undispatched-runs": {
            "task": "fin.detect_undispatched_runs",
            "schedule": 300.0,  # 5min
            "options": {"expires": 240},
        },
        # ADR-239 D5 (A18 L3 P2) — refresh anual de FIPE em 15/Jan às 03h UTC
        # (todos vehicles ativos). Janeiro é alinhado com IRPF do exercício
        # seguinte — base fiscal para cap rate líquido de veículos (Dezembro/<ano-1>).
        "fipe-refresh-annual": {
            "task": "fin.fipe.refresh_all_annual",
            "schedule": crontab(month_of_year=1, day_of_month=15, hour=3, minute=0),
        },
        # A33.l5 (ADR-307 F2) — drift estrutural nightly do extract_with_llm.
        # 06:15 UTC = 03:15 BRT (fora de pico); ~US$0,07/execução no cap
        # mês-calendário ADR-173 do workspace dogfood.
        "detect-extract-llm-drift": {
            "task": "fin.llm.detect_extract_llm_drift",
            "schedule": crontab(hour=6, minute=15),
        },
        # A33.l6 (W6-T05, ADR-212) — retenção de pipeline_artifacts: backfill
        # contínuo de rows superseded + relatório dry-run diário. 07:30 UTC =
        # 04:30 BRT (fora de pico, após o drift check). DELETE efetivo só com
        # prune_mode=delete (pipeline.json/env) — flip é PR separado gated no
        # dry-run com gate zerado.
        "prune-pipeline-artifacts-daily": {
            "task": "fin.prune_pipeline_artifacts",
            "schedule": crontab(hour=7, minute=30),
        },
    },
)


@worker_process_init.connect
def _init_worker_observability(**_: object) -> None:
    """Set up JSON logging + OTel in each Celery worker process (fork-safe)."""
    setup_logging()
    setup_otel(service_name="mathoms-worker")
    instrument_celery()
    _announce_executor_revision()


def _announce_executor_revision() -> None:
    """Anuncia no log qual revisão este processo executa (ADR-362)."""
    # É o único jeito de o preflight saber o que o worker VIVO roda: comparar o
    # run passado com o HEAD não diz nada sobre quem vai executar o próximo.
    get_logger("worker").info(
        "mathoms.worker.boot",
        extra={"executor_revision": settings.executor_revision or "desconhecido"},
    )
