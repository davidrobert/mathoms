"""Heartbeat in-stage do pipeline (A37.l12 · CTO-06).

``last_heartbeat_at`` era escrito só em run-start e stage-start — stage LLM
com muitos documentos excede os 15 min do watchdog (``detect_stuck_runs``,
ADR-172) e o run saudável flipa para ``failed``. O write abaixo é chamado
pelo loop de documentos via ``pipeline.live_progress.emit_item_progress``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text, update
from sqlalchemy.exc import OperationalError

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus

# Batida é best-effort: em SQLite (dev) a sessão do task segura o write-lock e
# o busy_timeout default (30s) BLOQUEAVA o loop de documentos a cada batida —
# foi o que estourou o hard time limit de 3600s no gate da A37 (run 866a1885).
_SQLITE_BUSY_TIMEOUT_MS = 200


def record_in_stage_heartbeat(run_id: str) -> bool:
    """CAS ``last_heartbeat_at=now`` só em run ``running`` (UPDATE condicional atômico, nunca read-modify-write cross-worker): run já flipado pelo watchdog não é ressuscitado nem renova heartbeat (anti flip-flop); ``True`` quando a batida aterrissou. Best-effort: lock contention vira ``False`` rápido (nunca bloqueia o loop de documentos); a batida seguinte cobre."""
    try:
        with SyncSessionLocal() as db:
            if db.get_bind().dialect.name == "sqlite":
                db.execute(text(f"PRAGMA busy_timeout = {_SQLITE_BUSY_TIMEOUT_MS}"))
            result = db.execute(
                update(PipelineRun)
                .where(PipelineRun.id == run_id, PipelineRun.status == PipelineRunStatus.running)
                .values(last_heartbeat_at=datetime.now(timezone.utc))
            )
            db.commit()
    except OperationalError:
        return False
    return result.rowcount == 1
