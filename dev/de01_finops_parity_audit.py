#!/usr/bin/env python3
"""Auditoria de paridade FinOps (Fase 0 do DE-01, emenda [[ADR-173]]): read-only, prova que ``llm_call_log`` reproduz o custo por ``(pipeline_run_id, stage)`` dentro de ±1 cent antes de dropar ``pipeline_run_costs`` (Fase 2) e conta as rows órfãs pré-hook (janela 2026-05-13 → 2026-07-02, custo exclusivo → exige snapshot cold). Roda em staging/prod via ``MATHOMS_DATABASE_URL_SYNC=... python3 dev/de01_finops_parity_audit.py``; exit 0 = 0 mismatch, exit 1 = mismatch (órfãs não são mismatch), **exit 3 = INDETERMINADO** (não consegui medir: env var ausente, ou tabela ausente no banco apontado). Sem a env var o default SQLite CRIA um arquivo vazio, a tabela "não existe" e a auditoria saía **0** — indistinguível de paridade confirmada (RV4-45 · A42.l3)."""

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

# "Não consegui medir" tem código próprio: 0 é reservado a paridade CONFIRMADA. Sem isto
# o gate da Fase 2 (dropar `pipeline_run_costs`) lia o verde de um banco vazio.
EXIT_OK, EXIT_MISMATCH, EXIT_INDETERMINADO = 0, 1, 3
_ENV_DB = "MATHOMS_DATABASE_URL_SYNC"


def _session_factory():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    default_db = REPO_ROOT / "mathoms.db"
    db_url = os.environ.get(_ENV_DB, f"sqlite:///{default_db}")
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
        return EXIT_MISMATCH
    # Os dois lados são alimentados pelo MESMO hook de escrita, então esta paridade prova
    # que o hook grava consistente nos dois sinks — NÃO que o custo esteja certo.
    print(f"OK — paridade confirmada ({total} rows, 0 mismatch); os dois sinks vêm do")
    print("mesmo hook, logo isto prova consistência de escrita, não custo correto.")
    print("Snapshot as órfãs antes da Fase 2.")
    return EXIT_OK


def _table_present(session) -> bool:
    from sqlalchemy import inspect

    return inspect(session.get_bind()).has_table("pipeline_run_costs")


def _run_audit(session) -> int:
    if not _table_present(session):
        alvo = os.environ.get(_ENV_DB) or f"default SQLite ({REPO_ROOT / 'mathoms.db'})"
        print(f"INDETERMINADO — `pipeline_run_costs` ausente em {alvo}.")
        print("Pré-migration, pós-Fase-2, OU banco errado. NÃO é paridade confirmada.")
        return EXIT_INDETERMINADO
    return _report(_reconcile(session))


def _env_ausente() -> bool:
    """Sem a env var o default aponta um SQLite local que o `create_engine` CRIA vazio —
    a tabela "não existe" e a auditoria saía 0. A condição estava só no docstring."""
    return not os.environ.get(_ENV_DB)


def main() -> int:
    if _env_ausente():
        print(f"INDETERMINADO — `{_ENV_DB}` não definida; a auditoria roda contra o banco")
        print("de staging/prod. Rodar sem ela mede um SQLite vazio e responderia 'OK'.")
        return EXIT_INDETERMINADO
    with _session_factory()() as session:
        return _run_audit(session)


if __name__ == "__main__":
    raise SystemExit(main())
