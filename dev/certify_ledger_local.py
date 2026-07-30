#!/usr/bin/env python3
"""Re-derivação in-process de E3+E4 sobre o E2 persistido — modo primário da skill
ledger-certify (ADR-302/343). Read-only: sem Celery, sem LLM, sem write no DB.

Semeia um ``InMemoryArtifactStore`` com o E2 vivo do workspace (mais recente por
``(stage canônico, key)`` — replica ``DBArtifactStore._get_latest_in_workspace``),
re-roda reconcile (E3) + categorize (E4) determinísticos com os flags/config
reais, e delega ao núcleo puro ``dev.ledger_certify_core`` (vereditos + drift +
relatório) sobre ``dev.ledger_conservation``. Zero-write é provado por contagem de
rows ``pipeline_artifacts`` / ``transaction_overrides`` antes/depois.

**Substrato E2 = workspace-latest (não run-pinado):** o E2 que o read-path do
pipeline efetivamente lê para os stages E2 do workspace. A divergência vs o E3/E4
gravado é drift esperado (código mudou pós-run OU artefato de run parcial,
ADR-080) — reportada, não tratada como perda.

Uso (do CHECKOUT PRINCIPAL, com o venv do repo — o worktree tem DB/STORAGE
vazios pois ``_PROJECT_ROOT`` segue o ``sys.path``):

    python3 dev/certify_ledger_local.py <email|uuid> [--run <run_id>] [--persist]

Os imports de backend são lazy: importar este módulo não exige env/DB.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_SKILL_SCRIPTS = _REPO_ROOT / ".claude" / "skills" / "ledger-certify" / "scripts"
if str(_SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SKILL_SCRIPTS))

from dev.ledger_certify_core import LedgerReport, build_report, format_report

_E2_STAGES = ("extract_statements", "extract_invoices", "extract_with_llm")
_BASELINE_STAGES = ("consolidate_baseline",)
_E3_STAGE = "reconcile_transactions"


# ─────────────────────────── leitura DB (read-only) ───────────────────────────


def _decrypt(payload: dict) -> dict:
    from backend.app.services.security.crypto import (
        decrypt_artifact_payload,
        is_encrypted_payload,
    )

    return decrypt_artifact_payload(payload) if is_encrypted_payload(payload) else payload


def _artifact_rows(session, ws: str, stages: tuple[str, ...]) -> list:
    from sqlalchemy import select

    from backend.app.models.pipeline_artifact import PipelineArtifact
    from pipeline.artifact_store import stage_aliases

    aliases = sorted({a for s in stages for a in stage_aliases(s)})
    stmt = select(PipelineArtifact).where(
        PipelineArtifact.workspace_id == ws,
        PipelineArtifact.stage.in_(aliases),
    )
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


def _blast_radius_or_empty(session, ws: str) -> dict:
    """Medição SECUNDÁRIA jamais derruba o entregável PRIMÁRIO (SQL cru sobre 5 colunas
    nullable com M2 destrutiva pendente); o ``rollback`` é obrigatório porque em
    PostgreSQL o statement falho aborta a transação (25P02) e derrubaria o
    ``_row_counts`` seguinte — que é a PROVA de zero-write."""
    from sqlalchemy.exc import SQLAlchemyError

    try:
        return _override_blast_radius(session, ws)
    except SQLAlchemyError as exc:
        session.rollback()
        print(
            f"[blast radius] não medido — schema divergente: {exc.__class__.__name__}",
            file=sys.stderr,
        )
        return {}


# ─────────────────────────── seed + re-derivação ───────────────────────────


def _seed_store(store, latest_e2: dict, latest_base: dict) -> list[dict]:
    """Semeia E2 + baseline no InMemory; devolve os payloads E2 (para o ledger)."""
    e2_payloads = []
    for (stage, key), payload in latest_e2.items():
        store.seed(stage, key, payload)
        e2_payloads.append(payload)
    for (stage, key), payload in latest_base.items():
        store.seed(stage, key, payload)
    return e2_payloads


def _build_context(session, ws: str, run_id: str | None, store):
    from backend.app.core.config import settings
    from backend.app.services.pipeline.pipeline_adapter import (
        build_config_overrides_from_db,
        build_config_store,
    )
    from backend.app.services.pipeline.run_context_factory import _read_imoveis_no_if
    from pipeline.context import WorkspaceContext

    tenant_root = Path(settings.STORAGE_ROOT).resolve() / ws
    return WorkspaceContext.for_tenant(
        tenant_root,
        config=build_config_overrides_from_db(ws, db=session),
        config_dir=_REPO_ROOT / "config",
        pipeline_run_id=run_id,
        artifact_store=store,
        workspace_id=ws,
        config_store=build_config_store(db=session),
        imoveis_no_if=_read_imoveis_no_if(ws, session),
    )


def _rederive_e3(ctx, store):
    """Reconcile in-process (serializer/key legados) — escreve só no InMemory.
    Devolve o ``ReconciliationStoreResult`` (skipped_inputs contextualiza o gap)."""
    from scripts.reconcile_transactions import _e3_build_adapter, _e3_run_reconciliation

    adapter, canon = _e3_build_adapter(ctx)
    return _e3_run_reconciliation(adapter, store, canon)


def _load_learned_rules(session, ws: str):
    from backend.app.services.categorization_rules_adapter import (
        load_categorization_rules_v2,
    )

    return load_categorization_rules_v2(workspace_id=ws, db=session)


def _dedup_v2_enabled(session, ws: str) -> bool:
    from backend.app.services.feature_flags_service import is_enabled_sync

    return is_enabled_sync(ws, "dedup_natural_key_v2_enabled", db=session)


def _rederive_e4(ctx, session, ws: str, store):
    """Categorize in-process PURO (sem learning-loop / persist — ambos escrevem).
    Serializa os 7 baldes via ``serialize_e4_artifacts`` (serialização de produção).
    Devolve ``(CategorizationResult, {balde: payload})``."""
    from pipeline.domain.services.e4_categorizer_adapter import E4CategorizerAdapter
    from pipeline.domain.services.e4_serialization import serialize_e4_artifacts
    from pipeline.domain.services.protecao_wiring import load_apolices

    adapter = E4CategorizerAdapter.from_configs(
        categorization=ctx.load_config("categorization.json"),
        family=ctx.load_config("family_members.json"),
        learned_rules_v2=_load_learned_rules(session, ws),
        dedup_natural_key_v2=_dedup_v2_enabled(session, ws),
    )
    result = adapter.categorize_via_store(store)
    return result, serialize_e4_artifacts(result, apolices=load_apolices(store))


def _fresh_e3(store) -> dict:
    """``{artifact_key: payload E3 fresco}`` lido do InMemory pós-reconcile."""
    return {key: store.read(_E3_STAGE, key) for key in store.list_keys(_E3_STAGE)}


def _rederive(session, ws: str, run_id: str | None):
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    seeds = _seed_store(
        store,
        _latest_payloads(session, ws, _E2_STAGES),
        _latest_payloads(session, ws, _BASELINE_STAGES),
    )
    ctx = _build_context(session, ws, run_id, store)
    e3_result = _rederive_e3(ctx, store)
    result, e4 = _rederive_e4(ctx, session, ws, store)
    return store, seeds, e3_result, result, e4


def certify(session, ws: str, run_id: str | None) -> LedgerReport:
    """Re-deriva E3+E4 e monta o LedgerReport. Read-only (zero-write provado)."""
    before = _row_counts(session, ws)
    store, seeds, e3_result, result, e4 = _rederive(session, ws, run_id)
    report = build_report(
        ws,
        run_id,
        seeds,
        e3_result,
        result,
        e4,
        _fresh_e3(store),
        _persisted_e3_by_key(session, ws),
    )
    report.counts_before = before
    report.blast_radius = _blast_radius_or_empty(session, ws)
    report.counts_after = _row_counts(session, ws)
    return report


# ─────────────────────────── CLI ───────────────────────────


def _persist(report: LedgerReport, text: str) -> None:
    from backend.app.core.config import settings

    run8 = (report.run_id or "norun")[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = Path(settings.STORAGE_ROOT).resolve() / report.workspace_id / "ledger_certify"
    out_dir = base / f"{ts}-{run8}"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "synthesis.md"
    target.write_text(text, encoding="utf-8")
    print(f"\n[persistido off-git] {target}")


def _silence_sql_echo() -> None:
    for name in ("sqlalchemy.engine", "sqlalchemy.engine.Engine"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _resolve_and_certify(session, args) -> LedgerReport | None:
    import resolve_ledger  # skill scripts já no sys.path (topo do módulo)

    ws = resolve_ledger._resolve_id(session, args.workspace)
    if ws is None:
        return None
    run_id = args.run or resolve_ledger._latest_run(session, ws)
    report = certify(session, ws, run_id)
    session.rollback()
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workspace", help="email ou uuid")
    parser.add_argument(
        "--run", default=None, help="run_id alvo (default: run completed mais recente)"
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="grava synthesis.md off-git em storage/<uuid>/ledger_certify/",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    from backend.app.core.database import SyncSessionLocal

    _silence_sql_echo()
    with SyncSessionLocal() as session:
        report = _resolve_and_certify(session, args)
    if report is None:
        print(f"workspace não encontrado: {args.workspace!r}")
        return 1
    text = format_report(report)
    print(text)
    if args.persist:
        _persist(report, text)
    return 0 if report.zero_write_ok else 3


if __name__ == "__main__":
    sys.exit(main())
