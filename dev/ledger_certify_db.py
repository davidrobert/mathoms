#!/usr/bin/env python3
"""Leitura DB (read-only) do harness ledger-certify — artefatos, runs e contagens.

Split de ``dev.certify_ledger_local`` em A42.l14: o arquivo encostou no teto de 500
linhas e a lane ainda lhe adiciona o substrato run-scoped da [[ADR-421]]. Aqui moram
só os leitores; os call-sites (``certify`` / ``_finish``) ficam no harness.

**Os nomes voltam ao harness por RE-EXPORT DE BINDING** (``from … import _x``), nunca
por chamada qualificada: quatro testes fazem ``monkeypatch.setattr(mod, "_row_counts"
| "_e3_of_run" | …)`` sobre ``certify_ledger_local``, e um call-site qualificado
(``db._row_counts(...)``) tornaria esses patches INERTES em silêncio — o teste passaria
verde sem exercitar nada. Provado por mutação: trocar o binding por chamada qualificada
reprova 4 testes.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dev.ledger_certify_entregue import EntregueRecusado

_E2_STAGES = ("extract_statements", "extract_invoices", "extract_with_llm")
_BASELINE_STAGES = ("consolidate_baseline",)
_E3_STAGE = "reconcile_transactions"


def _decrypt(payload: dict) -> dict:
    from backend.app.services.security.crypto import (
        decrypt_artifact_payload,
        is_encrypted_payload,
    )

    return decrypt_artifact_payload(payload) if is_encrypted_payload(payload) else payload


def _artifact_rows(session, ws: str, stages: tuple[str, ...], *, run_id: str | None = None) -> list:
    from sqlalchemy import select

    from backend.app.models.pipeline_artifact import PipelineArtifact
    from pipeline.artifact_store import stage_aliases

    aliases = sorted({a for s in stages for a in stage_aliases(s)})
    stmt = select(PipelineArtifact).where(
        PipelineArtifact.workspace_id == ws,
        PipelineArtifact.stage.in_(aliases),
    )
    if run_id is not None:
        stmt = stmt.where(PipelineArtifact.pipeline_run_id == run_id)
    return list(session.execute(stmt).scalars())


def _latest_by_canonical(rows: list) -> dict:
    """Colapsa para o mais recente por ``(stage canônico, key)`` — replica
    ``DBArtifactStore._get_latest_in_workspace`` (``created_at`` desc, ``id`` desc,
    através dos aliases legado↔descritivo)."""
    from pipeline.stage_spec import resolve_stage_name

    best: dict = {}
    for row in rows:
        unit = (resolve_stage_name(row.stage), row.artifact_key)
        incumbent = best.get(unit)
        if incumbent is None or (row.created_at, row.id) > (incumbent.created_at, incumbent.id):
            best[unit] = row
    return best


def _decrypt_latest(latest: dict) -> dict:
    return {unit: _decrypt(row.content_json) for unit, row in latest.items()}


def _latest_payloads(session, ws: str, stages: tuple[str, ...]) -> dict:
    return _decrypt_latest(_latest_by_canonical(_artifact_rows(session, ws, stages)))


def _persisted_e3_by_key(session, ws: str) -> dict:
    """E3 persistido mais recente por ``artifact_key`` (string) — para o drift."""
    latest = _latest_by_canonical(_artifact_rows(session, ws, (_E3_STAGE,)))
    return {key: _decrypt(row.content_json) for (stage, key), row in latest.items()}


def _require_run(session, ws: str, run_id: str):
    from backend.app.models.pipeline_run import PipelineRun

    run = session.get(PipelineRun, run_id)
    if run is None:
        raise EntregueRecusado(f"run não encontrado: {run_id}")
    if run.workspace_id != ws:
        raise EntregueRecusado(f"run {run_id} não pertence ao workspace")
    return run


def _e3_stage_log(session, run_id: str):
    from sqlalchemy import select

    from backend.app.models.pipeline_run import PipelineStageLog
    from pipeline.artifact_store import stage_aliases

    aliases = sorted(stage_aliases(_E3_STAGE))
    stmt = (
        select(PipelineStageLog)
        .where(
            PipelineStageLog.pipeline_run_id == run_id,
            PipelineStageLog.stage.in_(aliases),
        )
        .order_by(PipelineStageLog.started_at.desc())
    )
    return session.execute(stmt).scalars().first()


def _row_counts(session, ws: str) -> dict:
    from sqlalchemy import text

    art = session.execute(
        text("SELECT COUNT(*) FROM pipeline_artifacts WHERE workspace_id=:w"), {"w": ws}
    ).scalar()
    ovr = session.execute(
        text("SELECT COUNT(*) FROM transaction_overrides WHERE workspace_id=:w"), {"w": ws}
    ).scalar()
    return {"pipeline_artifacts": int(art or 0), "transaction_overrides": int(ovr or 0)}


_BLAST_SQL = """
SELECT
  SUM(CASE WHEN deleted_at IS NULL AND orphaned_at IS NULL THEN 1 ELSE 0 END) AS ativos,
  SUM(CASE WHEN deleted_at IS NULL AND orphaned_at IS NULL
            AND tx_valor_cents IS NOT NULL THEN 1 ELSE 0 END) AS ativos_com_snapshot,
  SUM(CASE WHEN deleted_at IS NULL AND orphaned_at IS NULL AND tx_valor_cents IS NOT NULL
            AND TRIM(COALESCE(tx_titular, '')) = '' THEN 1 ELSE 0 END) AS titular_vazio,
  SUM(CASE WHEN deleted_at IS NULL AND orphaned_at IS NULL
            AND tx_valor_cents IS NULL THEN 1 ELSE 0 END) AS sem_snapshot,
  SUM(CASE WHEN deleted_at IS NULL AND orphaned_at IS NULL
            AND natural_key_hash IS NULL THEN 1 ELSE 0 END) AS sem_ancora_v2,
  SUM(CASE WHEN deleted_at IS NULL AND orphaned_at IS NOT NULL THEN 1 ELSE 0 END) AS quarentenados,
  SUM(CASE WHEN deleted_at IS NOT NULL THEN 1 ELSE 0 END) AS soft_deleted
FROM transaction_overrides WHERE workspace_id = :w
"""


def _override_blast_radius(session, ws: str) -> dict:
    """Overrides ATIVOS ancorados em row E4 de ``titular`` vazio (carrier 2 da ADR-354),
    via snapshot ADR-282 — agregados só, nenhuma coluna de conteúdo sai do DB."""
    from sqlalchemy import text

    row = session.execute(text(_BLAST_SQL), {"w": ws}).mappings().one()
    return {k: int(v or 0) for k, v in row.items()}
