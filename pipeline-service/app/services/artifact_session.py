"""Sessão + ``DBArtifactStore`` por-stage para o executor HTTP (ADR-303).

Espelha ``_open_artifact_session`` / ``_commit_and_close_artifact_session``
do caminho Celery (``backend/app/tasks/pipeline_task.py``): sessão fresca por
stage libera o write-lock SQLite entre stages, e o hook de validação de
schema + criptografia (``DBArtifactStore.write``) roda também no modo HTTP.
"""

from __future__ import annotations

from typing import Iterable


class ArtifactStoreUnavailable(RuntimeError):
    """Executor sem acesso ao ``DBArtifactStore`` (ADR-303 D4)."""


def _new_session():
    from backend.app.core.database import SyncSessionLocal

    return SyncSessionLocal()


def open_artifact_store(
    *,
    workspace_id: str,
    run_id: str,
    base_run_id: str | None = None,
    base_run_fallback_stages: Iterable[str] = (),
):
    """Abre sessão nova + store para UM stage. Falha cedo e nomeada (D4)."""
    try:
        from backend.app.services.storage.db_artifact_store import DBArtifactStore
    except ImportError as exc:
        raise ArtifactStoreUnavailable(
            "pipeline-service requer o pacote 'backend' importável para executar "
            f"stages (DBArtifactStore, ADR-303 D4): {exc}"
        ) from exc

    try:
        session = _new_session()
    except Exception as exc:
        raise ArtifactStoreUnavailable(
            f"falha ao abrir sessão DB para o artifact store (ADR-303 D4): {exc}"
        ) from exc

    store = DBArtifactStore(
        session,
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        base_run_id=base_run_id,
        base_run_fallback_stages=frozenset(base_run_fallback_stages),
    )
    return session, store


def commit_and_close(session) -> None:
    if session is None:
        return
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def rollback_and_close(session) -> None:
    if session is None:
        return
    try:
        session.rollback()
    finally:
        session.close()


def close_by_outcome(session, stage: str, result) -> None:
    """Commit sse o desfecho preserva a transação do stage (ADR-357 §6) — a regra do loop in-process."""
    # `_run_stage` achata a exceção do runner em `success=False`: sem decidir pelo
    # desfecho, o commit levaria o que o stage escreveu antes de não entregar.
    from pipeline.stage_outcome import commits_stage_transaction, resolve_stage_outcome

    outcome = resolve_stage_outcome(stage, delivered=bool(result.success))
    if commits_stage_transaction(stage, outcome):
        commit_and_close(session)
    else:
        rollback_and_close(session)
