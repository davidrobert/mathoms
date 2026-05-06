"""After a pipeline run, mark each document with E2 extract presence."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.models.document import Document, DocumentStatus
from backend.app.repositories.pipeline_artifact_repository import PipelineArtifactRepository

# These doc type values are never processed by the deterministic E2 extractor —
# eles vivem em income_tax_br/ ou members/. IRPF tem extract próprio via
# E1.5a (`{stem}-1.5a_extract.json`); os demais não produzem JSON per-arquivo.
# Using raw strings to avoid SQLAlchemy enum vs str comparison edge cases.
_NO_E2_EXTRACT_TYPE_VALUES = {"irpf", "e1_members_json", "e1_5_baseline_json"}
_IRPF_E15A_EXTRACT_TYPES = {"irpf"}

# Doc types onde o extract E2 é **opcional** — quando presente, registramos
# True (badge "Extraído"); quando ausente, registramos None (badge "Processado")
# em vez de False ("Sem extrato"). Investimentos são roteados pelo E2 só
# quando o filename casa `investimentosposicao`/`carteirarenda`/`cdb*`; uploads
# rotulados como investimento mas com filename misclassified (ex.: Itaú XLS
# nomeado como `extratoconta` mas com posição de carteira) ficavam reportados
# como "Sem extrato" enganosamente.
_OPTIONAL_E2_EXTRACT_TYPE_VALUES = {"investment_report"}

# Stages onde E2 grava per-doc no DB (espelho de scripts/e2_extract.run_with_store).
# E2-llm é stub determinístico que registra arquivos delegados ao wrapper LLM.
_E2_DB_STAGES = ("E2-extratos", "E2-faturas", "E2-llm")


def _e15a_json_name(source_filename: str) -> str:
    """Mirror E1.5a write convention (stem + -1.5a_extract.json)."""
    return re.sub(
        r"(-0_original)?\.(pdf|csv|xls|xlsx|jpg|jpeg|png)$",
        "-1.5a_extract.json",
        source_filename,
        flags=re.IGNORECASE,
    )


def _e15a_base_stem(source_filename: str) -> str:
    """Strip de extensão + ``-0_original`` — mesmo formato de artifact_key em E1.5."""
    return re.sub(
        r"(-0_original)?\.(pdf|csv|xls|xlsx|jpg|jpeg|png)$",
        "",
        source_filename,
        flags=re.IGNORECASE,
    )


def _find_e15a_extract(e2_dir: Path, source_filename: str) -> Path | None:
    """Return the E1.5a extract Path for an IRPF source filename, or None."""
    if not e2_dir.exists():
        return None
    exact = e2_dir / _e15a_json_name(source_filename)
    if exact.exists():
        return exact
    base_stem = _e15a_base_stem(source_filename)
    pattern = re.compile(
        rf"^{re.escape(base_stem)}[a-z]?-1\.5a_extract\.json$",
        re.IGNORECASE,
    )
    for f in e2_dir.iterdir():
        if f.is_file() and pattern.match(f.name):
            return f
    return None


def has_e15a_artifact_in_db(db: Session, workspace_id: str, source_filename: str) -> bool:
    """Fallback DB para E1.5a — `MATHOMS_USE_DB_ARTIFACTS=True` não materializa em disco.

    Checa `pipeline_artifacts(stage='E1.5a', artifact_key=stem)`. Stem casa com
    `pipeline.stages.e15._artifact_key_for` (strip de `-0_original` + extensão).
    """
    stem = _e15a_base_stem(source_filename)
    repo = PipelineArtifactRepository(db)
    return repo.get_latest_for_workspace(workspace_id, stage="E1.5a", artifact_key=stem) is not None


def has_e2_artifact_in_db(db: Session, workspace_id: str, source_filename: str) -> bool:
    """Fallback DB para E2 (mesma motivação de `has_e15a_artifact_in_db`)."""
    stem = _e15a_base_stem(source_filename)
    repo = PipelineArtifactRepository(db)
    return any(
        repo.get_latest_for_workspace(workspace_id, stage=stage, artifact_key=stem) is not None
        for stage in _E2_DB_STAGES
    )


def _e2_json_name(source_filename: str) -> str:
    """Mirror ``scripts.e2_extract.make_output_name`` (avoid importing E2 stack)."""
    return re.sub(
        r"(-0_original)?\.(pdf|csv|xls|xlsx|jpg|jpeg|png)$",
        "-2_extract.json",
        source_filename,
        flags=re.IGNORECASE,
    )


def _find_e2_extract(e2_dir: Path, source_filename: str) -> Path | None:
    """Return the E2 extract Path for the given source filename, or None.

    Handles the case where E0 route renamed the file by appending an ``a``/``b``
    suffix (e.g. ``wise_extratoconta_2025-0_original.pdf`` →
    ``wise_extratoconta_2025a-0_original.pdf``) but the DB ``stored_path`` still
    holds the pre-rename name.  When the exact extract is missing we look for any
    extract whose stem matches the base stem + a single lowercase letter.
    """
    exact = e2_dir / _e2_json_name(source_filename)
    if exact.exists():
        return exact

    # Fuzzy: check for a/b/c… variants produced by E0 route disambiguation
    base_stem = re.sub(
        r"(-0_original)?\.(pdf|csv|xls|xlsx|jpg|jpeg|png)$",
        "",
        source_filename,
        flags=re.IGNORECASE,
    )
    pattern = re.compile(
        rf"^{re.escape(base_stem)}[a-z]-2_extract\.json$",
        re.IGNORECASE,
    )
    for f in e2_dir.iterdir():
        if f.is_file() and pattern.match(f.name):
            return f
    return None


def _read_extract_notes(extract_path: Path) -> str | None:
    """Read the ``notas`` array from an E2 extract JSON and return as newline-joined text.

    Returns None when there are no notes or the file cannot be parsed.
    """
    try:
        data = json.loads(extract_path.read_text(encoding="utf-8"))
        notes = data.get("notas") or []
        if not notes:
            return None
        return "\n".join(str(n) for n in notes if n)
    except Exception:
        return None


def apply_pipeline_e2_sync_to_documents(
    documents: Sequence[Document],
    tenant_root: Path,
    completed_at: datetime,
    db: Session | None = None,
) -> None:
    """Update pipeline timestamps, E2 flags, and promote ``ready`` → ``processed``.

    Called after a successful pipeline run. Idempotent for rows already ``processed``.

    Quando ``db`` é passado, IRPF e docs E2 (extratos / faturas / comprovantes)
    sem extract em disco são consultados na tabela ``pipeline_artifacts`` —
    necessário com ``MATHOMS_USE_DB_ARTIFACTS=True`` (E1.5 e E2 escrevem direto
    no DB sem materializar em disco).
    """
    e2_dir = tenant_root / "processed" / "E2_extracts"
    e2_dir.mkdir(parents=True, exist_ok=True)

    for doc in documents:
        fname = Path(doc.stored_path or "").name
        if not fname:
            continue

        doc.pipeline_last_run_at = completed_at

        # IRPF and member JSON types are not processed by the deterministic E2
        # extractor — clear any stale extract flag so they don't show as "Sem extrato".
        doc_type_val = (
            doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type or "")
        )
        if doc_type_val in _NO_E2_EXTRACT_TYPE_VALUES:
            if doc_type_val in _IRPF_E15A_EXTRACT_TYPES:
                has_extract = _find_e15a_extract(e2_dir, fname) is not None
                if not has_extract and db is not None and doc.workspace_id:
                    has_extract = has_e15a_artifact_in_db(db, doc.workspace_id, fname)
                doc.pipeline_e2_extract_ok = has_extract
                if has_extract and doc.needs_review:
                    doc.needs_review = False
            else:
                doc.pipeline_e2_extract_ok = None
            doc.pipeline_extract_notes = None
            if doc.status == DocumentStatus.ready:
                doc.status = DocumentStatus.processed
            continue

        extract_path = _find_e2_extract(e2_dir, fname)
        has_extract = extract_path is not None
        if not has_extract and db is not None and doc.workspace_id:
            has_extract = has_e2_artifact_in_db(db, doc.workspace_id, fname)

        if doc_type_val in _OPTIONAL_E2_EXTRACT_TYPE_VALUES and not has_extract:
            doc.pipeline_e2_extract_ok = None
        else:
            doc.pipeline_e2_extract_ok = has_extract
        doc.pipeline_extract_notes = _read_extract_notes(extract_path) if extract_path else None
        # Successful artefact extraction confirms the upload-time classification
        # was correct enough — clear the "incerta" flag set by the LLM fallback.
        if has_extract and doc.needs_review:
            doc.needs_review = False
        if doc.status == DocumentStatus.ready:
            doc.status = DocumentStatus.processed


def sync_documents_pipeline_e2_status(
    workspace_id: str,
    tenant_root: Path,
    completed_at: datetime,
) -> None:
    """Set ``pipeline_last_run_at`` and ``pipeline_e2_extract_ok`` for workspace docs.

    A document is considered to have an E2 extract if ``processed/E2_extracts/<stem>-2_extract.json``
    exists, where ``stem`` is derived from the inbox filename (same convention as E2).

    Documents in ``ready`` are transitioned to ``processed`` (pipeline concluiu para o workspace).
    """
    with SyncSessionLocal() as db:
        rows = (
            db.execute(
                select(Document).where(
                    Document.workspace_id == workspace_id,
                    Document.stored_path.isnot(None),
                    Document.status != DocumentStatus.error,
                )
            )
            .scalars()
            .all()
        )

        apply_pipeline_e2_sync_to_documents(rows, tenant_root, completed_at, db=db)

        db.commit()
