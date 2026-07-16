#!/usr/bin/env python3
"""Auditoria de paridade FinOps (Fase 0 do DE-01, emenda [[ADR-173]]): read-only, prova que ``llm_call_log`` reproduz o custo por ``(pipeline_run_id, stage)`` dentro de ±1 cent antes de dropar ``pipeline_run_costs`` (Fase 2) e conta as rows órfãs pré-hook (janela 2026-05-13 → 2026-07-02, custo exclusivo → exige snapshot cold). Roda em staging/prod via ``MATHOMS_DATABASE_URL_SYNC=... python3 dev/de01_finops_parity_audit.py``; exit 0 = 0 mismatch, exit 1 = mismatch (órfãs não são mismatch)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("MATHOMS_FERNET_KEY", "gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA0=")
os.environ.setdefault("MATHOMS_JWT_SECRET", "x" * 32)

_TOLERANCE_CENTS = 1


def _session_factory():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    default_db = REPO_ROOT / "mathoms.db"
    db_url = os.environ.get("MATHOMS_DATABASE_URL_SYNC", f"sqlite:///{default_db}")
    return sessionmaker(bind=create_engine(db_url, future=True), future=True)


def _llm_cents_for(session, *, run_id: str, stage: str) -> int | None:
    """Σ(llm_call_log.cost_usd) × 100 arredondado, ou None se não há twin."""
    from sqlalchemy import func, select

    from backend.app.models.llm_call_log import LLMCallLog

    total = session.execute(
        select(func.sum(LLMCallLog.cost_usd)).where(
            LLMCallLog.pipeline_run_id == run_id, LLMCallLog.stage == stage
        )
    ).scalar_one_or_none()
    return None if total is None else int(round(float(total) * 100))


def _classify_row(session, row) -> tuple[str, dict]:
    """``orphan`` (sem twin em llm_call_log), ``mismatch`` (>tolerância) ou ``ok``."""
    twin = _llm_cents_for(session, run_id=row.pipeline_run_id, stage=row.stage)
    if twin is None:
        return "orphan", {"run_id": row.pipeline_run_id, "cost_usd_cents": row.cost_usd_cents}
    if abs(twin - row.cost_usd_cents) > _TOLERANCE_CENTS:
        return "mismatch", {"run_id": row.pipeline_run_id, "prc": row.cost_usd_cents, "llm": twin}
    return "ok", {}


def _reconcile(session) -> dict:
    from sqlalchemy import select

    from backend.app.models.pipeline_run_cost import PipelineRunCost

    rows = session.execute(select(PipelineRunCost)).scalars().all()
    buckets: dict[str, list] = {"orphan": [], "mismatch": [], "ok": []}
    for row in rows:
        tag, payload = _classify_row(session, row)
        buckets[tag].append(payload)
    return {"total": len(rows), "mismatches": buckets["mismatch"], "orphans": buckets["orphan"]}


def _report(result: dict) -> int:
    total, mism, orph = result["total"], result["mismatches"], result["orphans"]
    print(f"pipeline_run_costs rows: {total}")
    print(f"órfãs pré-hook (só em pipeline_run_costs, exigem snapshot): {len(orph)}")
    print(f"mismatches (>{_TOLERANCE_CENTS} cent vs llm_call_log): {len(mism)}")
    for m in mism[:20]:
        print(f"  MISMATCH run={m['run_id']} prc={m['prc']} llm={m['llm']}")
    if mism:
        print("FALHOU — llm_call_log NÃO reproduz o custo; NÃO dropar pipeline_run_costs.")
        return 1
    print("OK — paridade confirmada (0 mismatch). Snapshot as órfãs antes da Fase 2.")
    return 0


def _table_present(session) -> bool:
    from sqlalchemy import inspect

    return inspect(session.get_bind()).has_table("pipeline_run_costs")


def _run_audit(session) -> int:
    if not _table_present(session):
        print("pipeline_run_costs ausente (pré-migration ou pós-Fase-2) — auditoria N/A.")
        return 0
    return _report(_reconcile(session))


def main() -> int:
    with _session_factory()() as session:
        return _run_audit(session)


if __name__ == "__main__":
    raise SystemExit(main())
