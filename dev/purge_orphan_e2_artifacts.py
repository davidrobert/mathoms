#!/usr/bin/env python3
"""Purga dirigida de artifacts E2-llm órfãos de reclassificação (A32.l1).

Contexto: docs reclassificados para fora do escopo do E2-llm (ex.:
``informe_previdencia_privada`` → ``documents.doc_type =
informe_rendimentos_anuais``) deixam para trás o artifact E2-llm gravado
sob a key antiga. ``_find_unprocessed_docs`` pula docs cuja key já existe
(``pipeline/stages/extract_with_llm.py``), então o órfão nunca se
auto-corrige e envenena o E3 a cada run.

Classificação (somente metadados — ``content_json`` é Fernet-encrypted
at-rest e nunca é lido/decriptado aqui):

- **orphan** (alvo de DELETE): artifact em stage E2-llm cujo documento
  (resolvido por prefixo ``content_hash[:12]`` na ``artifact_key``,
  ADR-084 — a FK ``document_id`` é NULL nas rows E2-llm) tem hoje
  ``doc_type`` processado exclusivamente por outro stage.
- **stale** (report-only, NUNCA deletado): artifact criado antes de
  2026-07-06 (PR #786/A28.l8 — writer passou a gravar ``banco``);
  vocabulário antigo (``instituicao`` sem ``banco``). Decisão Q1 do
  owner (2026-07-07): serão re-extraídos via LLM após a A32.l2, pelo
  script dirigido da A32.l5.
- **current** / **unmatched**: fora do escopo, apenas contabilizados.

Dry-run é o default; ``--execute`` muta o DB. O DELETE é restrito por
``id + workspace_id + stage + artifact_key`` e limitado por
``--max-delete`` (default 2) — impossível deletar além do alvo por
construção. Idempotente: segunda execução real encontra 0 órfãos.
Padrão de mutação destrutiva controlada:
``backend/app/services/internal_ops/pipeline_reset.py``.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

# Prefixo content-addressed das keys de artefato (ADR-084): sha256[:12].
_HASH_PREFIX_RE = re.compile(r"^[0-9a-f]{12}(?=_)")

# doc_types processados exclusivamente por stages não-E2-llm
# (extract_informes_anuais · extract_irpf_full/E1.5 · extract_comprovantes_bens).
# Artifact E2-llm apontando para doc nesses tipos = órfão de reclassificação.
DOC_TYPES_OUTSIDE_E2_LLM_SCOPE = frozenset(
    {"informe_rendimentos_anuais", "irpf", "comprovante_bem"}
)

# PR #786 (A28.l8, mergeado 2026-07-06): writer E2-llm passou a gravar
# ``banco``. Artifacts criados antes têm vocabulário stale (``instituicao``).
BANCO_VOCAB_CUTOFF_ISO = "2026-07-06"

VERDICT_ORPHAN = "orphan"
VERDICT_STALE = "stale"
VERDICT_CURRENT = "current"
VERDICT_UNMATCHED = "unmatched"


@dataclass(frozen=True)
class E2LlmArtifactFinding:
    """Veredito por artifact E2-llm — só metadados, nunca payload."""

    artifact_id: int
    workspace_id: str
    stage: str
    artifact_key: str
    created_at: str
    document_id: str | None
    doc_type: str | None
    verdict: str


def _e2_llm_stage_names() -> tuple[str, ...]:
    """Par descritivo↔legacy via stage_aliases (nunca literal único)."""
    from pipeline.artifact_store import stage_aliases  # import tardio

    return stage_aliases("extract_with_llm")


def _load_e2_llm_artifact_rows(session: Session) -> list[tuple]:
    stages = _e2_llm_stage_names()
    keys = ",".join(f":s{i}" for i in range(len(stages)))
    params = {f"s{i}": s for i, s in enumerate(stages)}
    return session.execute(
        text(
            "SELECT id, workspace_id, stage, artifact_key, created_at "
            f"FROM pipeline_artifacts WHERE stage IN ({keys}) "
            "ORDER BY created_at, id"
        ),
        params,
    ).all()


def _resolve_documents_by_prefix(
    session: Session, pairs: set[tuple[str, str]]
) -> dict[tuple[str, str], tuple[str, str | None]]:
    """(workspace_id, hash12) → (document_id, doc_type). Workspace-scoped."""
    out: dict[tuple[str, str], tuple[str, str | None]] = {}
    for workspace_id, prefix in sorted(pairs):
        row = session.execute(
            text(
                "SELECT id, doc_type FROM documents "
                "WHERE workspace_id = :ws AND content_hash LIKE :pref "
                "ORDER BY uploaded_at LIMIT 1"
            ),
            {"ws": workspace_id, "pref": f"{prefix}%"},
        ).first()
        if row is not None:
            out[(workspace_id, prefix)] = (row[0], row[1])
    return out


def _verdict_for(doc_type: str | None, matched: bool, created_at: str) -> str:
    if not matched:
        return VERDICT_UNMATCHED
    if doc_type in DOC_TYPES_OUTSIDE_E2_LLM_SCOPE:
        return VERDICT_ORPHAN
    if str(created_at)[:10] < BANCO_VOCAB_CUTOFF_ISO:
        return VERDICT_STALE
    return VERDICT_CURRENT


def _classify_row(
    row: tuple, docs: dict[tuple[str, str], tuple[str, str | None]]
) -> E2LlmArtifactFinding:
    artifact_id, workspace_id, stage, artifact_key, created_at = row
    match = _HASH_PREFIX_RE.match(artifact_key)
    doc = docs.get((workspace_id, match.group(0))) if match else None
    document_id, doc_type = doc if doc else (None, None)
    return E2LlmArtifactFinding(
        artifact_id=artifact_id,
        workspace_id=workspace_id,
        stage=stage,
        artifact_key=artifact_key,
        created_at=str(created_at),
        document_id=document_id,
        doc_type=doc_type,
        verdict=_verdict_for(doc_type, doc is not None, str(created_at)),
    )


def find_e2_llm_findings(session: Session) -> list[E2LlmArtifactFinding]:
    """Classifica todo artifact E2-llm do DB em orphan/stale/current/unmatched."""
    rows = _load_e2_llm_artifact_rows(session)
    pairs = {(ws, m.group(0)) for _, ws, _, key, _ in rows if (m := _HASH_PREFIX_RE.match(key))}
    docs = _resolve_documents_by_prefix(session, pairs)
    return [_classify_row(row, docs) for row in rows]


def _guard_max_delete(n_orphans: int, max_delete: int) -> None:
    if n_orphans > max_delete:
        raise RuntimeError(
            f"guard: {n_orphans} órfãos encontrados > --max-delete={max_delete}; "
            "nada foi deletado — revise o dry-run antes de aumentar o cap"
        )


def delete_orphans(
    session: Session, orphans: list[E2LlmArtifactFinding], *, max_delete: int
) -> int:
    """DELETE cirúrgico por id+workspace+stage+key; aborta se exceder o cap."""
    _guard_max_delete(len(orphans), max_delete)
    deleted = 0
    for f in orphans:
        result = session.execute(
            text(
                "DELETE FROM pipeline_artifacts "
                "WHERE id = :id AND workspace_id = :ws "
                "AND stage = :stage AND artifact_key = :key"
            ),
            {"id": f.artifact_id, "ws": f.workspace_id, "stage": f.stage, "key": f.artifact_key},
        )
        deleted += result.rowcount or 0
    return deleted


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

_LINE = "=" * 100


def _print_finding_table(title: str, findings: list[E2LlmArtifactFinding]) -> None:
    print(f"{title} ({len(findings)}):")
    if not findings:
        print("  (nenhum)")
        print()
        return
    print(f"  {'art_id':>6}  {'stage':<16}  {'artifact_key':<54}  {'doc_type':<27}  created_at")
    for f in findings:
        print(
            f"  {f.artifact_id:>6}  {f.stage:<16}  {f.artifact_key:<54}  "
            f"{(f.doc_type or '-'):<27}  {f.created_at[:19]}"
        )
    print()


def _print_report(findings: list[E2LlmArtifactFinding], *, execute: bool) -> None:
    by = lambda v: [f for f in findings if f.verdict == v]  # noqa: E731
    print(_LINE)
    print(f"Purga E2-llm órfãos (A32.l1) — {'EXECUTE' if execute else 'DRY-RUN'}")
    print(_LINE)
    print()
    _print_finding_table("ÓRFÃOS de reclassificação → DELETE", by(VERDICT_ORPHAN))
    _print_finding_table(
        "STALE vocabulário pré-2026-07-06 → REPORT-ONLY (re-extração via A32.l5, decisão Q1)",
        by(VERDICT_STALE),
    )
    _print_finding_table("SEM documento correspondente → REPORT-ONLY", by(VERDICT_UNMATCHED))
    print(
        f"Sumário: {len(by(VERDICT_ORPHAN))} orphan (delete) · {len(by(VERDICT_STALE))} stale "
        f"(mantidos) · {len(by(VERDICT_CURRENT))} current · "
        f"{len(by(VERDICT_UNMATCHED))} unmatched"
    )


def _print_footer_dry_run() -> None:
    print()
    print("Dry-run: nada foi deletado. Para executar (após backup do DB):")
    print("  python3 dev/purge_orphan_e2_artifacts.py --execute")
    print(_LINE)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_db_url() -> str:
    """Lê settings (mesmo path do backend), import tardio — --help sem env."""
    from backend.app.core.config import settings

    return settings.sync_database_url


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Purga artifacts E2-llm órfãos de reclassificação (A32.l1). Dry-run default."
    )
    parser.add_argument(
        "--execute", action="store_true", help="Executa o DELETE (default = dry-run, sem mutação)."
    )
    parser.add_argument(
        "--max-delete",
        type=int,
        default=2,
        help="Cap de segurança: aborta sem deletar se achar mais órfãos que isso (default: 2).",
    )
    parser.add_argument(
        "--db-url", default=None, help="URL SQLAlchemy sync (default: settings.sync_database_url)."
    )
    return parser.parse_args(argv)


def _run(session: Session, *, execute: bool, max_delete: int) -> int:
    findings = find_e2_llm_findings(session)
    orphans = [f for f in findings if f.verdict == VERDICT_ORPHAN]
    _print_report(findings, execute=execute)
    if not execute:
        _print_footer_dry_run()
        return 0
    try:
        deleted = delete_orphans(session, orphans, max_delete=max_delete)
        session.commit()
    except Exception as exc:
        session.rollback()
        print(f"\nFALHA: rollback aplicado. Erro: {exc}")
        return 2
    print(f"\nDeletados: {deleted} artifact(s). Stale/current/unmatched intactos.")
    print(_LINE)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    engine = create_engine(args.db_url or _resolve_db_url(), future=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as session:
        return _run(session, execute=args.execute, max_delete=args.max_delete)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
