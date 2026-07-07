#!/usr/bin/env python3
"""Re-extração DIRIGIDA de artifacts E2-llm abaixo de versão-alvo (A32.l5, ADR-311).

Seleciona rows de ``pipeline_artifacts`` em stage E2-llm cuja
``prompt_version`` (coluna consultável desde a migration ``a32l5promptver``)
é inferior à versão-alvo — NULL ≡ versão desconhecida/0 (rows
pré-migration, sem backfill). Em ``--execute``:

1. **Invalida**: DELETE cirúrgico por ``id + workspace_id + stage +
   artifact_key`` — a key deixa de existir e ``_find_unprocessed_docs``
   (``pipeline/stages/extract_with_llm.py``) volta a enfileirar o doc.
2. **Dispara**: reseta ``documents.pipeline_last_run_at`` /
   ``pipeline_e2_extract_ok`` dos documentos correspondentes (resolvidos
   por prefixo ``content_hash[:12]`` da key, ADR-084) para que o modo
   incremental (ADR-080) os inclua no allowlist da próxima run.

**Nenhuma chamada LLM acontece aqui** — o custo de re-extração é do owner
e o disparo real é a próxima run do pipeline (gate A32.l7, decisão Q1).
Re-extração automática em bump de versão fica explicitamente fora
(ADR-311 D3; cap de custo ADR-173).

Dry-run é o default; somente metadados são lidos (``content_json`` é
Fernet-encrypted at-rest e nunca é decriptado). Guard ``--max-invalidate``
aborta sem mutação se o alvo exceder o cap. Idempotente: segunda execução
real encontra 0 stale. Padrão: ``dev/purge_orphan_e2_artifacts.py`` (A32.l1).
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

from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

# Prefixo content-addressed das keys de artefato (ADR-084): sha256[:12].
_HASH_PREFIX_RE = re.compile(r"^[0-9a-f]{12}(?=_)")


@dataclass(frozen=True)
class StaleE2LlmArtifact:
    """Artifact E2-llm abaixo da versão-alvo — só metadados, nunca payload."""

    artifact_id: int
    workspace_id: str
    stage: str
    artifact_key: str
    prompt_version: str | None
    created_at: str
    document_id: str | None


def _e2_llm_stage_names() -> tuple[str, ...]:
    """Par descritivo↔legacy via stage_aliases (nunca literal único)."""
    from pipeline.artifact_store import stage_aliases  # import tardio

    return stage_aliases("extract_with_llm")


def parse_semver(version: str | None) -> tuple[int, ...]:
    """``"1.3.0"`` → ``(1, 3, 0)``; NULL/inválida → ``(0,)`` (desconhecida ≡ 0)."""
    if not version:
        return (0,)
    try:
        return tuple(int(part) for part in version.strip().split("."))
    except ValueError:
        return (0,)


def _current_prompt_version() -> str:
    from pipeline.llm.prompts.e2_llm import PROMPT_VERSION  # import tardio

    return PROMPT_VERSION


def _has_prompt_version_column(session: Session) -> bool:
    """DB pré-migration ``a32l5promptver`` não tem a coluna — toda row é
    versão desconhecida/0 por definição (ADR-311 D4)."""
    inspector = inspect(session.get_bind())
    return "prompt_version" in {c["name"] for c in inspector.get_columns("pipeline_artifacts")}


def _load_e2_llm_rows(session: Session) -> list[tuple]:
    stages = _e2_llm_stage_names()
    version_col = (
        "prompt_version" if _has_prompt_version_column(session) else "NULL AS prompt_version"
    )
    keys = ",".join(f":s{i}" for i in range(len(stages)))
    params = {f"s{i}": s for i, s in enumerate(stages)}
    return session.execute(
        text(
            f"SELECT id, workspace_id, stage, artifact_key, {version_col}, "
            "created_at, document_id "
            f"FROM pipeline_artifacts WHERE stage IN ({keys}) "
            "ORDER BY created_at, id"
        ),
        params,
    ).all()


def _artifact_from_row(row: tuple) -> StaleE2LlmArtifact:
    return StaleE2LlmArtifact(
        artifact_id=row[0],
        workspace_id=row[1],
        stage=row[2],
        artifact_key=row[3],
        prompt_version=row[4],
        created_at=str(row[5]),
        document_id=row[6],
    )


def find_stale_artifacts(
    session: Session, *, target_version: str, created_before: str | None = None
) -> list[StaleE2LlmArtifact]:
    """Artifacts E2-llm com ``prompt_version < target`` (NULL ≡ 0); ``created_before`` (ISO) separa gerações quando NULL em massa (rows pré-migration não têm backfill, ADR-311 D4) — precisão para o gate A32.l7."""
    target = parse_semver(target_version)
    return [
        _artifact_from_row(row)
        for row in _load_e2_llm_rows(session)
        if parse_semver(row[4]) < target
        and (created_before is None or str(row[5])[:10] < created_before)
    ]


def _guard_max_invalidate(n_stale: int, max_invalidate: int) -> None:
    if n_stale > max_invalidate:
        raise RuntimeError(
            f"guard: {n_stale} artifacts stale > --max-invalidate={max_invalidate}; "
            "nada foi invalidado — revise o dry-run antes de aumentar o cap"
        )


def _delete_artifact(session: Session, artifact: StaleE2LlmArtifact) -> int:
    result = session.execute(
        text(
            "DELETE FROM pipeline_artifacts "
            "WHERE id = :id AND workspace_id = :ws "
            "AND stage = :stage AND artifact_key = :key"
        ),
        {
            "id": artifact.artifact_id,
            "ws": artifact.workspace_id,
            "stage": artifact.stage,
            "key": artifact.artifact_key,
        },
    )
    return result.rowcount or 0


def _requeue_document(session: Session, artifact: StaleE2LlmArtifact) -> int:
    """Reseta flags de pipeline do doc dono da key — habilita re-extração incremental."""
    match = _HASH_PREFIX_RE.match(artifact.artifact_key)
    if match is None:
        return 0
    result = session.execute(
        text(
            "UPDATE documents SET pipeline_last_run_at = NULL, pipeline_e2_extract_ok = NULL "
            "WHERE workspace_id = :ws AND content_hash LIKE :pref"
        ),
        {"ws": artifact.workspace_id, "pref": f"{match.group(0)}%"},
    )
    return result.rowcount or 0


def invalidate_stale(
    session: Session, stale: list[StaleE2LlmArtifact], *, max_invalidate: int
) -> tuple[int, int]:
    """DELETE cirúrgico + re-queue dos docs. Retorna (deleted, requeued)."""
    _guard_max_invalidate(len(stale), max_invalidate)
    deleted = requeued = 0
    for artifact in stale:
        deleted += _delete_artifact(session, artifact)
        requeued += _requeue_document(session, artifact)
    return deleted, requeued


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

_LINE = "=" * 100


def _print_stale_table(stale: list[StaleE2LlmArtifact], target_version: str) -> None:
    print(f"Artifacts E2-llm com prompt_version < {target_version} ({len(stale)}):")
    if not stale:
        print("  (nenhum)")
        print()
        return
    print(f"  {'art_id':>6}  {'stage':<16}  {'artifact_key':<54}  {'version':<10}  created_at")
    for a in stale:
        print(
            f"  {a.artifact_id:>6}  {a.stage:<16}  {a.artifact_key:<54}  "
            f"{(a.prompt_version or 'NULL(=0)'):<10}  {a.created_at[:19]}"
        )
    print()


def _print_report(stale: list[StaleE2LlmArtifact], *, target_version: str, execute: bool) -> None:
    print(_LINE)
    print(f"Re-extração dirigida E2-llm (A32.l5, ADR-311) — {'EXECUTE' if execute else 'DRY-RUN'}")
    print(_LINE)
    print()
    _print_stale_table(stale, target_version)


def _print_footer_dry_run() -> None:
    print("Dry-run: nada foi invalidado. Para executar (após backup do DB):")
    print("  python3 dev/reextract_stale_e2_llm.py --execute")
    print("A re-extração real acontece na PRÓXIMA run do pipeline (custo LLM do owner).")
    print(_LINE)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_db_url() -> str:
    """Lê settings (mesmo path do backend), import tardio — --help sem env."""
    from backend.app.core.config import settings

    return settings.sync_database_url


def _add_selection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--target-version",
        default=None,
        help="Versão-alvo semver (default: PROMPT_VERSION atual do prompt E2-llm).",
    )
    parser.add_argument(
        "--created-before",
        default=None,
        metavar="YYYY-MM-DD",
        help=(
            "Restringe a artifacts criados antes desta data ISO — separa gerações "
            "quando prompt_version é NULL em massa (rows pré-migration)."
        ),
    )


def _add_execution_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Executa DELETE + re-queue (default = dry-run, sem mutação).",
    )
    parser.add_argument(
        "--max-invalidate",
        type=int,
        default=15,
        help="Cap de segurança: aborta sem invalidar se achar mais stale que isso (default: 15).",
    )
    parser.add_argument(
        "--db-url", default=None, help="URL SQLAlchemy sync (default: settings.sync_database_url)."
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Invalida artifacts E2-llm abaixo de versão-alvo para re-extração dirigida "
            "(A32.l5, ADR-311). Dry-run default; nenhuma chamada LLM é feita."
        )
    )
    _add_selection_args(parser)
    _add_execution_args(parser)
    return parser.parse_args(argv)


def _execute_invalidation(
    session: Session, stale: list[StaleE2LlmArtifact], max_invalidate: int
) -> int:
    if not _has_prompt_version_column(session):
        print("ABORT: DB sem coluna prompt_version (migration a32l5promptver não aplicada).")
        print("Rode `alembic upgrade head` antes de --execute; dry-run segue disponível.")
        return 2
    try:
        deleted, requeued = invalidate_stale(session, stale, max_invalidate=max_invalidate)
        session.commit()
    except Exception as exc:
        session.rollback()
        print(f"\nFALHA: rollback aplicado. Erro: {exc}")
        return 2
    print(f"Invalidados: {deleted} artifact(s); {requeued} documento(s) re-enfileirado(s).")
    print("Nenhuma chamada LLM foi feita — a próxima run do pipeline re-extrai.")
    print(_LINE)
    return 0


def _run(
    session: Session,
    *,
    target_version: str,
    execute: bool,
    max_invalidate: int,
    created_before: str | None = None,
) -> int:
    stale = find_stale_artifacts(
        session, target_version=target_version, created_before=created_before
    )
    _print_report(stale, target_version=target_version, execute=execute)
    if not execute:
        _print_footer_dry_run()
        return 0
    return _execute_invalidation(session, stale, max_invalidate)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    target_version = args.target_version or _current_prompt_version()
    engine = create_engine(args.db_url or _resolve_db_url(), future=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as session:
        return _run(
            session,
            target_version=target_version,
            execute=args.execute,
            max_invalidate=args.max_invalidate,
            created_before=args.created_before,
        )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
