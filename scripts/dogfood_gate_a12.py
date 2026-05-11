#!/usr/bin/env python3
"""Gate técnico do dogfood A12.cat-learning-loop — entrypoint (internals em ``dev/_dogfood_gate_a12/``). Não substitui gate humano UX; cobre invariantes mensuráveis (sticky manual, mês fechado, blacklist, caps, reverts). Idempotente (DB scratch). Uso: ``python3 scripts/dogfood_gate_a12.py``."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dev._dogfood_gate_a12.bootstrap import bootstrap  # noqa: E402

_SCRATCH, _DB_FILE, _STORAGE_ROOT = bootstrap()

# pylint: disable=wrong-import-position
import backend.app.models  # noqa: F401,E402 — registra models no metadata
from backend.app.core.database import engine  # noqa: E402
from dev._dogfood_gate_a12.pipeline import async_setup, run_pipeline_sync  # noqa: E402
from dev._dogfood_gate_a12.render import write_outputs  # noqa: E402


def _exit_code(verdict: str) -> int:
    if verdict == "PASS":
        return 0
    if verdict == "FAIL":
        return 1
    return 2


async def main() -> int:
    print(f"[dogfood-gate] DB: {_DB_FILE}", file=sys.stderr)
    print(f"[dogfood-gate] storage root: {_STORAGE_ROOT}", file=sys.stderr)
    user_id, ws_id, total_txs, closed = await async_setup()
    print(f"[dogfood-gate] workspace_id={ws_id} txs={total_txs}", file=sys.stderr)
    report = run_pipeline_sync(ws_id, user_id, closed, total_txs)
    json_path, md_path = write_outputs(report, _SCRATCH)
    print(f"[dogfood-gate] JSON: {json_path}", file=sys.stderr)
    print(f"[dogfood-gate] MD:   {md_path}", file=sys.stderr)
    print(f"[dogfood-gate] verdict: {report.verdict}")
    await engine.dispose()
    return _exit_code(report.verdict)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
