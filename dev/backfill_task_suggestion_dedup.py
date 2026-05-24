#!/usr/bin/env python3
"""Backfill `dedup_key` em rows legadas de `task_suggestions` + supersede de duplicatas pending (ADR-267)."""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("task_suggestion.backfill")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def _extract_title(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("title")


def _extract_category(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("category")


def _compute_key_for_row(row: Any) -> str | None:
    """sha256 a partir de proposed_payload + source. None se title ausente."""
    from backend.app.services.task_suggestion_dedup import compute_task_suggestion_dedup_key

    title = _extract_title(row.proposed_payload)
    category = _extract_category(row.proposed_payload)
    if not title:
        return None
    return compute_task_suggestion_dedup_key(row.source, title, category)


def _backfill_keys(session, dry_run: bool) -> tuple[int, int]:
    """Preenche dedup_key onde NULL. Retorna (filled, skipped_payload_invalido)."""
    from backend.app.models.task import TaskSuggestion

    rows = session.query(TaskSuggestion).filter(TaskSuggestion.dedup_key.is_(None)).all()
    filled = 0
    skipped = 0
    for row in rows:
        key = _compute_key_for_row(row)
        if key is None:
            logger.warning("skip ws=%s id=%s payload sem title", row.workspace_id, row.id)
            skipped += 1
            continue
        row.dedup_key = key
        filled += 1
    if not dry_run and filled:
        session.flush()
    return filled, skipped


def _group_pending_by_key(session) -> dict[tuple[str, str], list[Any]]:
    """Agrupa pending por (workspace_id, dedup_key); ordena cada bucket newest-first."""
    from backend.app.models.task import TaskSuggestion

    pending = (
        session.query(TaskSuggestion)
        .filter(TaskSuggestion.status == "pending")
        .filter(TaskSuggestion.dedup_key.is_not(None))
        .order_by(
            TaskSuggestion.workspace_id,
            TaskSuggestion.dedup_key,
            TaskSuggestion.created_at.desc(),
        )
        .all()
    )
    by_key: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for r in pending:
        by_key[(r.workspace_id, r.dedup_key)].append(r)
    return by_key


def _supersede_losers(losers: list[Any], winner: Any, now: datetime) -> None:
    """Marca cada loser como superseded apontando o run vencedor."""
    for loser in losers:
        loser.status = "superseded"
        loser.superseded_at = now
        loser.superseded_by_run_id = winner.source_run_id


def _supersede_duplicates(session, dry_run: bool) -> int:
    """Para cada (workspace_id, dedup_key) com >1 pending, mantém a mais nova; supersede o resto."""
    by_key = _group_pending_by_key(session)
    superseded = 0
    now = datetime.now(timezone.utc)
    for (ws_id, key), rows in by_key.items():
        if len(rows) <= 1:
            continue
        winner, *losers = rows
        logger.info("supersede ws=%s key=%s losers=%d", ws_id, key[:12], len(losers))
        _supersede_losers(losers, winner, now)
        superseded += len(losers)
    if not dry_run and superseded:
        session.flush()
    return superseded


def _finalize_transaction(
    session, dry_run: bool, filled: int, skipped: int, superseded: int
) -> None:
    if dry_run:
        session.rollback()
        logger.info("DRY-RUN — filled=%d skipped=%d superseded=%d", filled, skipped, superseded)
    else:
        session.commit()
        logger.info("COMMIT — filled=%d skipped=%d superseded=%d", filled, skipped, superseded)


def run_backfill(dry_run: bool) -> int:
    """Executa backfill numa única transação. Retorna 0 (ok) ou 1 (erro)."""
    from backend.app.core.database import SyncSessionLocal

    with SyncSessionLocal() as session:
        try:
            filled, skipped = _backfill_keys(session, dry_run)
            superseded = _supersede_duplicates(session, dry_run)
            _finalize_transaction(session, dry_run, filled, skipped, superseded)
        except Exception as exc:
            session.rollback()
            logger.exception("backfill failed: %s", exc)
            return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="commit (default: dry-run)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    _setup_logging(args.verbose)
    return run_backfill(dry_run=not args.apply)


if __name__ == "__main__":
    sys.exit(main())
