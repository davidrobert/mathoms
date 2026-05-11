#!/usr/bin/env python3
"""Cleanup single-tenant pré-produção — preserva keep list. Detalhes em RUNBOOK §5.3."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import create_engine, event, text  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

# Tabelas com FK direta para workspaces.id. Filtradas em runtime via
# ``_table_has_workspace_id`` — sem a coluna (``stage_reviews``, ``bank_accounts``,
# ``data_export_requests``) cascade via parent. Order-independent.
_DIRECT_WORKSPACE_TABLES: tuple[str, ...] = (
    "pipeline_artifacts", "pipeline_runs", "documents",
    "transaction_overrides", "workspace_category_overrides", "categorization_rules",
    "report_publications", "feature_flags", "decisions", "audit_logs",
    "tasks", "task_attachments", "task_suggestions",
    "family_members", "categories", "goals", "risks",
    "reports", "report_layouts",
    "pipeline_configs", "institution_configs", "transfer_configs", "llm_configs",
    "llm_call_log", "password_vault",
    "suggestions", "notifications", "workspace_notes",
    "workspace_invitations", "workspace_members",
)  # fmt: skip


def _resolve_db_url() -> str:
    """Lê settings (mesmo path do backend) e devolve URL sync."""
    from backend.app.core.config import settings  # noqa: WPS433 — import tardio

    return settings.sync_database_url


def _build_engine(url: str) -> Engine:
    """Engine síncrono com PRAGMA foreign_keys ligado em SQLite."""
    engine = create_engine(url, future=True)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _record):  # noqa: WPS430
            cur = dbapi_conn.cursor()
            try:
                cur.execute("PRAGMA foreign_keys=ON")
            finally:
                cur.close()

    return engine


def _table_exists(session: Session, table: str) -> bool:
    """SQLite + Postgres compatível. False se a migration ainda não rodou."""
    url = str(session.get_bind().url)
    if url.startswith("sqlite"):
        row = session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": table},
        ).first()
        return row is not None
    row = session.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_name=:t"),
        {"t": table},
    ).first()
    return row is not None


def _table_has_workspace_id(session: Session, table: str) -> bool:
    """Garante que a coluna existe antes de gerar SQL com ``workspace_id``."""
    if not _table_exists(session, table):
        return False
    url = str(session.get_bind().url)
    if url.startswith("sqlite"):
        rows = session.execute(text(f"PRAGMA table_info({table})")).all()
        return any(r[1] == "workspace_id" for r in rows)
    row = session.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name='workspace_id'"
        ),
        {"t": table},
    ).first()
    return row is not None


def _bind_in_clause(ids: list[str], prefix: str = "w") -> tuple[str, dict[str, str]]:
    """Gera ``:w0,:w1,...`` + dict de params para uso em ``IN (...)``."""
    keys = ",".join(f":{prefix}{i}" for i in range(len(ids)))
    params = {f"{prefix}{i}": v for i, v in enumerate(ids)}
    return keys, params


def _safe_count(session: Session, table: str, where: str, params: dict) -> int:
    """COUNT(*) defensivo — retorna 0 se a tabela/coluna não existe."""
    if not _table_exists(session, table):
        return 0
    if "workspace_id" in where and not _table_has_workspace_id(session, table):
        return 0
    return int(
        session.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {where}"), params).scalar() or 0
    )


def _list_workspaces(session: Session, keep_emails: set[str]) -> list[dict]:
    """Inventário dos workspaces fora da keep list, com counts úteis."""
    rows = session.execute(
        text(
            "SELECT w.id, w.name, w.created_at, COALESCE(u.email, '<no-owner>') AS email "
            "FROM workspaces w LEFT JOIN users u ON u.id = w.owner_id ORDER BY w.created_at"
        )
    ).all()
    out = []
    for ws_id, ws_name, created_at, email in rows:
        if email in keep_emails:
            continue
        out.append(_workspace_summary(session, ws_id, ws_name, created_at, email))
    return out


def _workspace_summary(session: Session, ws_id: str, ws_name: str, created_at, email: str) -> dict:
    """Linha tabular: id, owner_email, counts úteis, created_at."""
    return {
        "id": ws_id,
        "name": ws_name,
        "email": email,
        "created_at": str(created_at)[:19] if created_at else "?",
        **_workspace_counts(session, ws_id),
    }


def _workspace_counts(session: Session, ws_id: str) -> dict[str, int]:
    """Counts úteis para a linha tabular do dry-run."""
    p = {"ws": ws_id}
    return {
        "artifacts": _safe_count(session, "pipeline_artifacts", "workspace_id=:ws", p),
        "documents": _safe_count(session, "documents", "workspace_id=:ws", p),
        "overrides": _safe_count(session, "transaction_overrides", "workspace_id=:ws", p)
        + _safe_count(session, "workspace_category_overrides", "workspace_id=:ws", p),
        "rules": _safe_count(session, "categorization_rules", "workspace_id=:ws", p),
        "reports": _safe_count(session, "reports", "workspace_id=:ws", p),
        "audits": _safe_count(session, "audit_logs", "workspace_id=:ws", p),
    }


def _aggregate_totals(session: Session, ws_ids: list[str]) -> dict[str, int]:
    """Agrega counts por tabela para o sumário do dry-run."""
    if not ws_ids:
        return {t: 0 for t in _DIRECT_WORKSPACE_TABLES} | {"users": 0, "decision_events": 0}
    bind_keys, params = _bind_in_clause(ws_ids)
    totals = _count_direct_tables(session, bind_keys, params)
    totals["decision_events"] = _count_decision_events(session, bind_keys, params)
    totals["users"] = len(_orphaned_users(session, ws_ids))
    return totals


def _count_direct_tables(session: Session, bind_keys: str, params: dict) -> dict[str, int]:
    """COUNT por tabela em ``_DIRECT_WORKSPACE_TABLES`` (com guard de coluna)."""
    totals: dict[str, int] = {}
    for table in _DIRECT_WORKSPACE_TABLES:
        if not _table_has_workspace_id(session, table):
            totals[table] = 0
            continue
        totals[table] = int(
            session.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE workspace_id IN ({bind_keys})"),
                params,
            ).scalar()
            or 0
        )
    return totals


def _count_decision_events(session: Session, bind_keys: str, params: dict) -> int:
    """``decision_events`` cascade via ``decisions`` — count indireto."""
    if not (_table_exists(session, "decision_events") and _table_exists(session, "decisions")):
        return 0
    return int(
        session.execute(
            text(
                f"SELECT COUNT(*) FROM decision_events WHERE decision_id IN "
                f"(SELECT id FROM decisions WHERE workspace_id IN ({bind_keys}))"
            ),
            params,
        ).scalar()
        or 0
    )


def _orphaned_users(session: Session, deleted_ws_ids: list[str]) -> list[str]:
    """Owners cujos workspaces foram todos deletados E sem membership preservado."""
    if not deleted_ws_ids:
        return []
    bind_keys, params = _bind_in_clause(deleted_ws_ids)
    candidates = _candidate_owners(session, bind_keys, params)
    return [uid for uid in candidates if _is_orphan(session, uid, bind_keys, params)]


def _candidate_owners(session: Session, bind_keys: str, params: dict) -> list[str]:
    """Distinct owner_id dos workspaces a deletar."""
    rows = session.execute(
        text(f"SELECT DISTINCT owner_id FROM workspaces WHERE id IN ({bind_keys})"),
        params,
    ).all()
    return [row[0] for row in rows]


def _is_orphan(session: Session, user_id: str, bind_keys: str, params: dict) -> bool:
    """User órfão = sem ws preservado E sem membership em ws preservado."""
    p = {"u": user_id, **params}
    if _count_kept_owned_workspaces(session, p, bind_keys) > 0:
        return False
    return _count_kept_memberships(session, p, bind_keys) == 0


def _count_kept_owned_workspaces(session: Session, params: dict, bind_keys: str) -> int:
    sql = f"SELECT COUNT(*) FROM workspaces WHERE owner_id=:u AND id NOT IN ({bind_keys})"
    return int(session.execute(text(sql), params).scalar() or 0)


def _count_kept_memberships(session: Session, params: dict, bind_keys: str) -> int:
    if not _table_exists(session, "workspace_members"):
        return 0
    sql = (
        "SELECT COUNT(*) FROM workspace_members "
        f"WHERE user_id=:u AND workspace_id NOT IN ({bind_keys})"
    )
    return int(session.execute(text(sql), params).scalar() or 0)


def _delete_workspaces(
    session: Session,
    ws_ids: list[str],
    orphan_users: list[str],
) -> None:
    """Hard delete em transação única. PRAGMA foreign_keys cascade cobre filhos."""
    if not ws_ids:
        return
    bind_keys, params = _bind_in_clause(ws_ids)
    _delete_children(session, bind_keys, params)
    session.execute(text(f"DELETE FROM workspaces WHERE id IN ({bind_keys})"), params)
    _delete_orphan_users(session, orphan_users)


def _delete_children(session: Session, bind_keys: str, params: dict) -> None:
    """Defense in depth: deleta filhas antes do parent (caso pragma falhe)."""
    for table in _DIRECT_WORKSPACE_TABLES:
        if not _table_has_workspace_id(session, table):
            continue
        session.execute(
            text(f"DELETE FROM {table} WHERE workspace_id IN ({bind_keys})"),
            params,
        )


def _delete_orphan_users(session: Session, orphan_users: list[str]) -> None:
    if not orphan_users:
        return
    keys, params = _bind_in_clause(orphan_users, prefix="u")
    session.execute(text(f"DELETE FROM users WHERE id IN ({keys})"), params)


def _purge_blob_store(ws_ids: list[str]) -> int:
    """Remove ``storage/<ws_id>/`` em disco. Retorna número de pastas removidas."""
    storage_root = _REPO_ROOT / "storage"
    if not storage_root.exists():
        return 0
    removed = 0
    for ws_id in ws_ids:
        ws_dir = storage_root / ws_id
        if ws_dir.exists():
            shutil.rmtree(ws_dir)
            removed += 1
    return removed


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

_LINE = "=" * 79


def _print_dry_run(workspaces: list[dict], totals: dict[str, int], keep_emails: set[str]) -> None:
    """Header + tabela + sumário totais + instruções."""
    print(_LINE)
    print("Mathoms Workspace Cleanup — DRY RUN")
    print(_LINE)
    print()
    print(f"Workspaces preservados (keep list): {', '.join(sorted(keep_emails))}")
    print()
    print(f"Workspaces a deletar ({len(workspaces)} total):")
    print()
    if not workspaces:
        print("  (nada a deletar — todos workspaces estão na keep list)")
        print()
        return
    _print_workspace_table(workspaces)
    _print_totals(workspaces, totals)
    _print_footer()


def _print_workspace_table(workspaces: list[dict]) -> None:
    header = (
        f"  {'workspace_id':<38} {'owner_email':<32} "
        f"{'artifs':>7} {'docs':>5} {'ovrd':>5} {'rules':>5} {'reps':>5} {'audits':>7} {'created':<19}"
    )
    print(header)
    print(f"  {'-' * (len(header) - 2)}")
    for w in workspaces:
        print(
            f"  {w['id']:<38} {(w['email'] or '')[:32]:<32} "
            f"{w['artifacts']:>7} {w['documents']:>5} {w['overrides']:>5} "
            f"{w['rules']:>5} {w['reports']:>5} {w['audits']:>7} {w['created_at']:<19}"
        )
    print()


def _print_totals(workspaces: list[dict], totals: dict[str, int]) -> None:
    overrides = totals.get("transaction_overrides", 0) + totals.get(
        "workspace_category_overrides", 0
    )
    print("Totais a deletar:")
    print(f"  - {len(workspaces)} workspaces")
    print(f"  - {totals['users']} usuários órfãos (owners sem outro workspace)")
    print(f"  - {totals.get('pipeline_artifacts', 0)} pipeline_artifacts")
    print(f"  - {totals.get('pipeline_runs', 0)} pipeline_runs")
    print(f"  - {totals.get('documents', 0)} documents")
    print(f"  - {overrides} overrides (transaction + category)")
    print(f"  - {totals.get('categorization_rules', 0)} categorization_rules")
    print(f"  - {totals.get('audit_logs', 0)} audit_logs")
    print(f"  - {totals.get('reports', 0)} reports")
    print(f"  - {totals.get('decisions', 0)} decisions ({totals['decision_events']} events)")
    print(f"  - {totals.get('goals', 0)} goals")
    print(f"  - {totals.get('family_members', 0)} family_members")
    print(f"  - {totals.get('workspace_members', 0)} workspace_members")
    print()


def _print_footer() -> None:
    print("Para EXECUTAR o destrutivo (irreversível):")
    print("  python3 dev/purge_test_workspaces.py --apply")
    print()
    print("[Para incluir blob store em disco adicione --include-blob-store]")
    print(_LINE)


def _confirm_destructive() -> bool:
    """Prompt interativo — exige string exata ``DELETE-ALL``."""
    print()
    print(
        "ATENÇÃO: operação irreversível. Backup do DB antes de prosseguir é responsabilidade sua."
    )
    answer = input("Digite 'DELETE-ALL' para confirmar (qualquer outra coisa cancela): ").strip()
    return answer == "DELETE-ALL"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Purga workspaces de teste preservando keep list.")
    parser.add_argument(
        "--keep",
        action="append",
        default=None,
        help="Email de workspace owner a preservar (pode repetir). Default: 5@5.com",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Executa destrutivo (default = dry-run).",
    )
    parser.add_argument(
        "--include-blob-store",
        action="store_true",
        help="Também remove storage/<workspace_id>/ em disco.",
    )
    return parser.parse_args(argv)


def _run_apply(
    session: Session,
    workspaces: list[dict],
    totals: dict[str, int],
    keep_emails: set[str],
    include_blob_store: bool,
) -> int:
    """Executa destrutivo após confirmação. Retorna exit code."""
    ws_ids = [w["id"] for w in workspaces]
    if not ws_ids:
        print("Nada a deletar — keep list já cobre todos os workspaces.")
        return 0
    _print_dry_run(workspaces, totals, keep_emails)
    if not _confirm_destructive():
        print("Cancelado.")
        return 1
    return _do_apply(session, ws_ids, totals, keep_emails, include_blob_store)


def _do_apply(
    session: Session,
    ws_ids: list[str],
    totals: dict[str, int],
    keep_emails: set[str],
    include_blob_store: bool,
) -> int:
    """Caminho destrutivo após confirmação. Retorna exit code."""
    orphan_users = _orphaned_users(session, ws_ids)
    rc = _try_delete(session, ws_ids, orphan_users)
    if rc != 0:
        return rc
    blobs_removed = _purge_blob_store(ws_ids) if include_blob_store else 0
    _print_apply_summary(
        session, ws_ids, orphan_users, totals, keep_emails, include_blob_store, blobs_removed
    )
    return 0


def _try_delete(session: Session, ws_ids: list[str], orphan_users: list[str]) -> int:
    """Wrapper transação + rollback; retorna 0 em sucesso, 2 em falha."""
    try:
        _delete_workspaces(session, ws_ids, orphan_users)
        session.commit()
    except Exception as exc:
        session.rollback()
        print(f"FALHA: rollback aplicado. Erro: {exc!r}")
        return 2
    return 0


def _print_apply_summary(
    session: Session,
    ws_ids: list[str],
    orphan_users: list[str],
    totals: dict[str, int],
    keep_emails: set[str],
    include_blob_store: bool,
    blob_dirs_removed: int,
) -> None:
    """Imprime contagem final + lista preservada + verify hint."""
    print()
    print(_format_apply_line(ws_ids, orphan_users, totals))
    print(f"Workspaces preserved: {', '.join(sorted(keep_emails))}")
    if include_blob_store:
        print(f"Blob store: {blob_dirs_removed} pastas removidas de storage/.")
    remaining = session.execute(text("SELECT COUNT(*) FROM workspaces")).scalar()
    print(f"Verify: SELECT COUNT(*) FROM workspaces; -- atual: {remaining}")


def _format_apply_line(ws_ids: list[str], orphan_users: list[str], totals: dict[str, int]) -> str:
    return (
        f"Deleted {len(ws_ids)} workspaces, {len(orphan_users)} users, "
        f"{totals.get('pipeline_artifacts', 0)} artifacts, "
        f"{totals.get('audit_logs', 0)} audit_logs, "
        f"{totals.get('documents', 0)} documents, "
        f"{totals.get('reports', 0)} reports."
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    keep_emails: set[str] = set(args.keep) if args.keep else {"5@5.com"}
    engine = _build_engine(_resolve_db_url())
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as session:
        workspaces = _list_workspaces(session, keep_emails)
        ws_ids = [w["id"] for w in workspaces]
        totals = _aggregate_totals(session, ws_ids)
        if not args.apply:
            _print_dry_run(workspaces, totals, keep_emails)
            return 0
        return _run_apply(session, workspaces, totals, keep_emails, args.include_blob_store)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
