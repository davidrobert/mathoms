#!/usr/bin/env python3
"""Re-derivação in-process de E3+E4 sobre o E2 persistido — modo primário da skill
ledger-certify (ADR-302/343). Read-only: sem Celery, sem LLM, sem write no DB.

Semeia um ``InMemoryArtifactStore`` com o E2 vivo do workspace (mais recente por
``(stage canônico, key)`` — replica ``DBArtifactStore._get_latest_in_workspace``),
re-roda reconcile (E3) + categorize (E4) determinísticos com os flags/config
reais, e delega ao núcleo puro ``dev.ledger_certify_core`` (vereditos + drift +
relatório) sobre ``dev.ledger_conservation``. Zero-write é provado por contagem de
rows ``pipeline_artifacts`` / ``transaction_overrides`` antes/depois.

**Escopo assimétrico por stage ([[ADR-421]] D3, conformidade [[ADR-241]]):** o E2 é
lido pela política do run (workspace-latest — é o read-path de produção, e
run-escopá-lo reintroduziria o universo subdimensionado da ADR-241 §Contexto); o
**E3 é run-scoped**. A divergência vs o E4 gravado é drift esperado (código mudou
pós-run, artefato de run parcial (ADR-080), OU a config deste harness diverge da do
run num eixo que nenhum canal de ``remocoes`` declara) — reportada, não tratada como
perda. Remoção declarada dos dois lados NÃO conta como divergência: ``_e3_count``
normaliza por ``remocoes`` (A42.l20).

**Default = sombra** (E2→E3, ``collapse_enforce`` omitido). Não pontua a KR-B.
``--entregue --run <id>`` adiciona o detector sobre o E3 persistido daquele run
(única linha ``[numerador KR-B]``). Workspace-latest é recusado no modo entregue.

Uso (do CHECKOUT PRINCIPAL, com o venv do repo — o worktree tem DB/STORAGE
vazios pois ``_PROJECT_ROOT`` segue o ``sys.path``):

    python3 dev/certify_ledger_local.py <email|uuid> [--run <run_id>] [--persist]
    python3 dev/certify_ledger_local.py <email|uuid> --entregue --run <run_id>

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

# Re-export por BINDING (A42.l14): `monkeypatch.setattr(mod, "_row_counts")` só
# intercepta porque o nome mora NESTE módulo. Chamada qualificada (`db._row_counts`)
# tornaria os 4 patches dos testes inertes em silêncio — provado por mutação.
from dev.ledger_certify_db import (  # noqa: F401
    _BASELINE_STAGES,
    _BLAST_SQL,
    _E2_STAGES,
    _E3_STAGE,
    _artifact_rows,
    _decrypt,
    _decrypt_latest,
    _e2_payloads_with_census,
    _e3_stage_log,
    _latest_by_canonical,
    _latest_payloads,
    _override_blast_radius,
    _persisted_e3_by_key,
    _require_run,
    _row_counts,
)
from dev.ledger_certify_entregue import (
    EntregueRecusado,
    evidence_from_retention,
    require_pinned_run,
)
from dev.ledger_conservation import cross_group_summary

# ─────────────────────────── leitura DB (read-only) ───────────────────────────


def _e3_of_run(session, ws: str, run_id: str) -> dict:
    """E3 persistido daquele run — não workspace-latest."""
    latest = _latest_by_canonical(_artifact_rows(session, ws, (_E3_STAGE,), run_id=run_id))
    return {key: _decrypt(row.content_json) for (_stage, key), row in latest.items()}


def _persisted_e3_subject(session, ws: str, run_id: str | None) -> dict:
    """Substrato do veredito — E3 do run pinado ([[ADR-421]] D3, conformidade [[ADR-241]])."""
    # ADR-241 §Alternativas (a) rejeitou "mais-recente-por-key" para E3: congelaria dedup
    # parcial entre runs. `_persisted_e3_by_key` era essa alternativa dentro do instrumento.
    # Sem run pinado não há sujeito — herdar workspace-latest seria a herança silenciosa
    # que a D6 proíbe.
    return _e3_of_run(session, ws, run_id) if run_id is not None else {}


def _entregue_evidence(session, ws: str, run_id: str) -> dict:
    _require_run(session, ws, run_id)
    if not _e3_of_run(session, ws, run_id):
        raise EntregueRecusado(f"run {run_id} sem artefato E3 persistido")
    log = _e3_stage_log(session, run_id)
    summary = getattr(log, "output_summary", None) if log is not None else None
    revision = getattr(log, "executor_revision", None) if log is not None else None
    return evidence_from_retention(run_id, summary, revision)


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
    from pipeline.domain.services.cross_document_collapser import (
        CrossDocumentCollapser,
        OverrideRetentionGuard,
    )
    from scripts.reconcile_transactions import _e3_build_adapter, _e3_run_reconciliation

    # A40.l2 PR1b — o colapsador entra AQUI e não em produção: a medição precisa rodar
    # dentro do caminho real (`reconcile_via_store`), mas o stage não deve gastar CPU
    # produzindo candidato que nenhum consumidor de produção lê.
    adapter, canon = _e3_build_adapter(
        ctx,
        cross_document_collapser=CrossDocumentCollapser(
            retention_guard=OverrideRetentionGuard.sem_overrides()
        ),
    )
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


def _seed_e3(store, e3_by_key: dict) -> None:
    for key, payload in e3_by_key.items():
        store.seed(_E3_STAGE, key, payload)


def _rederive_entregue(session, ws: str, run_id: str, e3_by_key: dict):
    """Categoriza o E3 persistido — sem reconcile, sem enforce."""
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    _seed_e3(store, e3_by_key)
    ctx = _build_context(session, ws, run_id, store)
    return _rederive_e4(ctx, session, ws, store)


def _rederive(session, ws: str, run_id: str | None):
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    latest_e2, e2_census = _e2_payloads_with_census(session, ws, run_id)
    seeds = _seed_store(store, latest_e2, _latest_payloads(session, ws, _BASELINE_STAGES))
    ctx = _build_context(session, ws, run_id, store)
    e3_result = _rederive_e3(ctx, store)
    result, e4 = _rederive_e4(ctx, session, ws, store)
    return store, seeds, e3_result, result, e4, e2_census


def _certify_core(session, ws: str, run_id: str | None) -> LedgerReport:
    """Re-deriva E3+E4 e monta o LedgerReport, SEM fechar a prova de zero-write."""
    before = _row_counts(session, ws)
    store, seeds, e3_result, result, e4, e2_census = _rederive(session, ws, run_id)
    report = build_report(
        ws,
        run_id,
        seeds,
        e3_result,
        result,
        e4,
        _fresh_e3(store),
        _persisted_e3_subject(session, ws, run_id),
    )
    report.e2_provenance = e2_census
    report.counts_before = before
    return report


def _finish(session, ws: str, report: LedgerReport) -> LedgerReport:
    """Fecha a prova de zero-write. ORDEM É A PROVA: o `rollback` do blast radius degradado
    apaga a escrita pendente que a 2ª contagem tem de ver (rationale no doc da lane A40.l1).
    Mora aqui, e não no fim de cada modo, porque `certify_entregue` re-media DEPOIS do
    blast radius e ressuscitava o falso-verde justamente no modo que pontua a KR-B."""
    report.counts_after = _row_counts(session, ws)
    report.blast_radius = _blast_radius_or_empty(session, ws)
    return report


def certify(session, ws: str, run_id: str | None) -> LedgerReport:
    """Re-deriva E3+E4 e monta o LedgerReport. Read-only (zero-write provado)."""
    return _finish(session, ws, _certify_core(session, ws, run_id))


def _attach_entregue(report: LedgerReport, result_e, e4_e, evidence: dict) -> None:
    report.cross_group_entregue = cross_group_summary(e4_e, result_e.cash_flow.transferencias_count)
    report.entregue = evidence


def certify_entregue(session, ws: str, run_id: str) -> LedgerReport:
    """Sombra + detector sobre o E3 persistido do ``run_id``. Fail-closed no pin."""
    evidence = _entregue_evidence(session, ws, run_id)
    e3_run = _e3_of_run(session, ws, run_id)
    report = _certify_core(session, ws, run_id)
    result_e, e4_e = _rederive_entregue(session, ws, run_id, e3_run)
    _attach_entregue(report, result_e, e4_e, evidence)
    return _finish(session, ws, report)


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
    if args.entregue:
        report = certify_entregue(session, ws, require_pinned_run(args.run))
    else:
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
    parser.add_argument(
        "--entregue",
        action="store_true",
        help="prova KR-B no E3 persistido do --run (obrigatório); sombra segue no relatório",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    from backend.app.core.database import SyncSessionLocal

    _silence_sql_echo()
    try:
        with SyncSessionLocal() as session:
            report = _resolve_and_certify(session, args)
    except EntregueRecusado as exc:
        print(f"entregue recusado: {exc}", file=sys.stderr)
        return 2
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
