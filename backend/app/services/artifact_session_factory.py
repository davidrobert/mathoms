"""Sessão + ``DBArtifactStore`` por-stage para executores fora do Celery (ADR-303 D1).

Consumido pelo CLI ``run-stage`` do orchestrator (A3.cli): a mecânica de
sessão vive no backend porque ``pipeline/**`` não abre ``Session`` própria
(ADR-256) — o executor injeta o store pronto em ``ctx.artifact_store``.
Espelha ``_open_artifact_session`` / ``_commit_and_close_artifact_session``
do caminho Celery (``backend/app/tasks/pipeline_task.py``).
"""

from __future__ import annotations

from typing import Iterable, Tuple

from sqlalchemy.orm import Session

from backend.app.services.db_artifact_store import DBArtifactStore


class ArtifactSessionUnavailable(RuntimeError):
    """Executor sem acesso ao ``DBArtifactStore`` (ADR-303 D4)."""


def _new_session_or_raise() -> Session:
    try:
        from backend.app.core.database import SyncSessionLocal

        return SyncSessionLocal()
    except Exception as exc:
        raise ArtifactSessionUnavailable(
            f"falha ao abrir sessão DB para o artifact store (ADR-303 D4): {exc}"
        ) from exc


def open_artifact_store(
    *,
    workspace_id: str,
    run_id: str,
    base_run_id: str | None = None,
    base_run_fallback_stages: Iterable[str] = (),
) -> Tuple[Session, DBArtifactStore]:
    """Abre sessão nova + store para UM stage. Falha cedo e nomeada (D4)."""
    session = _new_session_or_raise()
    store = DBArtifactStore(
        session,
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        base_run_id=base_run_id,
        base_run_fallback_stages=frozenset(base_run_fallback_stages),
    )
    return session, store


def commit_and_close(session: Session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def rollback_and_close(session: Session) -> None:
    try:
        session.rollback()
    finally:
        session.close()
