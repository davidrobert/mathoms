#!/usr/bin/env python3
"""Backfill encryption staging/dev em pipeline_artifacts.content_json (ADR-231). --dry-run default. Prod via Celery task em W3-T04."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from sqlalchemy import and_, or_

# Allow running as standalone script from repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.database import SyncSessionLocal  # noqa: E402
from backend.app.models.pipeline_artifact import PipelineArtifact  # noqa: E402
from backend.app.services.security.crypto import (  # noqa: E402
    encrypt_artifact_payload,
    is_encrypted_payload,
)

CURSOR_DIR = REPO_ROOT / "_scratch"


def _payload_fingerprint(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]


def _cursor_path(workspace_id: str | None) -> Path:
    name = workspace_id or "global"
    return CURSOR_DIR / f"backfill_{name}_cursor.txt"


def _read_cursor(workspace_id: str | None) -> str | None:
    path = _cursor_path(workspace_id)
    if path.exists():
        return path.read_text().strip() or None
    return None


def _write_cursor(workspace_id: str | None, last_id: str) -> None:
    CURSOR_DIR.mkdir(parents=True, exist_ok=True)
    _cursor_path(workspace_id).write_text(last_id)


def _clear_cursor(workspace_id: str | None) -> None:
    path = _cursor_path(workspace_id)
    if path.exists():
        path.unlink()


def _pg_plaintext_filter(query):
    # Filtra rows cujo content_json não tem flag _encrypted: true (JSONB only).
    return query.filter(
        or_(
            PipelineArtifact.content_json.op("->>")("_encrypted").is_(None),
            PipelineArtifact.content_json.op("->>")("_encrypted") != "true",
        )
    )


def _query_pending(session, workspace_id: str | None, after_id: str | None, batch_size: int):
    query = session.query(PipelineArtifact)
    if workspace_id:
        query = query.filter(PipelineArtifact.workspace_id == workspace_id)
    if after_id:
        query = query.filter(PipelineArtifact.id > after_id)
    dialect = session.get_bind().dialect.name if session.get_bind() is not None else "unknown"
    if dialect == "postgresql":
        return (
            _pg_plaintext_filter(query).order_by(PipelineArtifact.id.asc()).limit(batch_size).all()
        )
    rows = query.order_by(PipelineArtifact.id.asc()).limit(batch_size * 4).all()
    return [r for r in rows if not is_encrypted_payload(r.content_json)][:batch_size]


def _count_pending(session, workspace_id: str | None) -> int:
    query = session.query(PipelineArtifact)
    if workspace_id:
        query = query.filter(PipelineArtifact.workspace_id == workspace_id)
    dialect = session.get_bind().dialect.name if session.get_bind() is not None else "unknown"
    if dialect == "postgresql":
        return int(_pg_plaintext_filter(query).count())
    return sum(1 for r in query.all() if not is_encrypted_payload(r.content_json))


def _print_dry_run_sample(session, workspace_id: str | None, batch_size: int) -> None:
    sample = _query_pending(session, workspace_id, None, min(5, batch_size))
    for row in sample:
        print(
            f"  sample id={row.id} workspace={row.workspace_id} stage={row.stage} "
            f"key={row.artifact_key} fingerprint_before={_payload_fingerprint(row.content_json or {})}"
        )
    print("--dry-run: no changes applied.")


def _encrypt_loop(
    session, workspace_id, batch_size, sleep_ms, after_id, total_pending
) -> tuple[int, str | None]:
    processed = 0
    while True:
        batch = _query_pending(session, workspace_id, after_id, batch_size)
        if not batch:
            return processed, after_id
        for row in batch:
            row.content_json = encrypt_artifact_payload(row.content_json or {})
            after_id = row.id
        session.commit()
        processed += len(batch)
        _write_cursor(workspace_id, after_id)
        print(f"  committed batch {len(batch)} (cumulative {processed}/{total_pending})")
        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000.0)


def _run_apply(session, workspace_id, batch_size, sleep_ms, resume, total_pending) -> int:
    after_id = _read_cursor(workspace_id) if resume else None
    if after_id:
        print(f"Resuming after id={after_id}")
    processed, _ = _encrypt_loop(
        session, workspace_id, batch_size, sleep_ms, after_id, total_pending
    )
    _clear_cursor(workspace_id)
    print(
        f"Done. {processed} rows encrypted. Run `VACUUM (ANALYZE) pipeline_artifacts` to reclaim bloat."
    )
    return processed


def backfill(
    *, dry_run: bool, workspace_id: str | None, batch_size: int, sleep_ms: int, resume: bool
) -> int:
    """Executa backfill. Retorna número de rows processadas."""
    session = SyncSessionLocal()
    try:
        total_pending = _count_pending(session, workspace_id)
        print(f"Pending plaintext rows: {total_pending}")
        if dry_run:
            _print_dry_run_sample(session, workspace_id, batch_size)
            return 0
        return _run_apply(session, workspace_id, batch_size, sleep_ms, resume, total_pending)
    finally:
        session.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Aplica writes; sem essa flag roda em --dry-run."
    )
    parser.add_argument("--workspace", default=None, help="Restringe ao workspace UUID.")
    parser.add_argument("--batch", type=int, default=500, help="Rows por commit (default 500).")
    parser.add_argument(
        "--sleep-ms", type=int, default=200, help="Pause entre batches em ms (default 200)."
    )
    parser.add_argument("--no-resume", action="store_true", help="Ignora cursor; reinicia do zero.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.apply:
        confirm = input(
            f"Aplicar encryption em pipeline_artifacts (workspace={args.workspace or 'ALL'}, batch={args.batch})? [y/N] "
        )
        if confirm.strip().lower() not in {"y", "yes"}:
            print("Cancelado.")
            return 1
    backfill(
        dry_run=not args.apply,
        workspace_id=args.workspace,
        batch_size=args.batch,
        sleep_ms=args.sleep_ms,
        resume=not args.no_resume,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
