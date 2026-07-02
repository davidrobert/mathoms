#!/usr/bin/env python3
"""Snapshot CSV de ``llm_call_log`` pré/pós migração de semver (A20.l12 · ADR-261).

Exporta as rows cujo ``prompt_version`` está (ou estava) em formato legado
``<slug>-v<semver>`` para auditoria antes/depois da migration ``a20l12semver``.

Uso:
    python3 dev/snapshot_llm_call_log_history.py --all-legacy [--out <path.csv>]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

_COLUMNS = (
    "id",
    "workspace_id",
    "stage",
    "model_name",
    "prompt_version",
    "prompt_version_legacy",
    "tokens_in",
    "tokens_out",
    "cost_usd",
    "created_at",
)


def snapshot(out_path: Path) -> int:
    from sqlalchemy import or_, select

    from backend.app.core.database import SyncSessionLocal
    from backend.app.models.llm_call_log import LLMCallLog

    session = SyncSessionLocal()
    try:
        rows = (
            session.execute(
                select(LLMCallLog)
                .where(
                    or_(
                        LLMCallLog.prompt_version_legacy.is_not(None),
                        LLMCallLog.prompt_version.like("%-v%"),
                    )
                )
                .order_by(LLMCallLog.created_at)
            )
            .scalars()
            .all()
        )
        with out_path.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(_COLUMNS)
            for row in rows:
                writer.writerow([getattr(row, col) for col in _COLUMNS])
        return len(rows)
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-legacy", action="store_true", required=True)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("_scratch/llm_call_log_pre_semver_migration.csv"),
    )
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    count = snapshot(args.out)
    print(f"snapshot: {count} rows legadas → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
