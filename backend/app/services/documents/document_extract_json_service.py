"""Composite: lê o extrato E2 (JSON) de um documento (A6e.4 slice 10).

Extraído de ``api/documents.py::get_document_extract_json`` (endpoint
de debug/dev). Estratégias de match (stored_path exato → bank_code +
doc_type + period) seguem paridade com `document_pipeline_sync`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.app.core.database import SyncSessionLocal
from backend.app.models.document import Document, DocumentType
from backend.app.repositories.pipeline_artifact_repository import PipelineArtifactRepository
from backend.app.services.pipeline.document_pipeline_sync import (
    _E2_DB_STAGES,
    _e15a_base_stem,
    _find_e2_extract,
    _find_e15a_extract,
)
from backend.app.services.security.crypto import read_artifact_content
from backend.app.services.storage import StorageService


class DocumentExtractError(Exception):
    """Falha ao localizar/ler extrato. Router → 404/500."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class ExtractJsonResult:
    filename: str
    data: dict
    all_candidates: list[str]


_DOC_TYPE_KEYWORDS = {
    DocumentType.credit_card_bill: ["fatura"],
    DocumentType.bank_statement: ["extrato"],
}


def read_document_extract_json(
    doc: Document,
    *,
    workspace_id: str,
    storage: StorageService,
) -> ExtractJsonResult:
    """Retorna o JSON do E2 para o doc. Levanta ``DocumentExtractError``
    quando o diretório, lista de extratos ou arquivo-alvo não existe."""
    e2_dir = storage.tenant_root(workspace_id) / "processed" / "E2_extracts"

    # IRPF: extract vive em `-1.5a_extract.json` (E1.5a, per-arquivo).
    # Quando MATHOMS_USE_DB_ARTIFACTS=True, E1.5 escreve só no DB — fallback obrigatório.
    if doc.doc_type == DocumentType.irpf:
        db_data = _read_irpf_e15a_from_db(doc, workspace_id)
        if db_data is not None:
            return ExtractJsonResult(
                filename=db_data["filename"],
                data=db_data["data"],
                all_candidates=db_data["all_candidates"],
            )
        if not e2_dir.exists():
            raise DocumentExtractError(
                "Extrato IRPF (E1.5a) não encontrado para este documento",
                status_code=404,
            )
        target = _match_irpf_e15a(doc, e2_dir)
        all_candidates = sorted(f.name for f in e2_dir.glob("*-1.5a_extract.json"))
        if target is None:
            raise DocumentExtractError(
                "Extrato IRPF (E1.5a) não encontrado para este documento",
                status_code=404,
            )
    else:
        # E2 (extratos / faturas / comprovantes): com MATHOMS_USE_DB_ARTIFACTS=True
        # o stage E2 grava só em pipeline_artifacts. DB primário, disco fallback.
        db_data = _read_e2_from_db(doc, workspace_id)
        if db_data is not None:
            return ExtractJsonResult(
                filename=db_data["filename"],
                data=db_data["data"],
                all_candidates=db_data["all_candidates"],
            )
        if not e2_dir.exists():
            raise DocumentExtractError("Nenhum extrato disponível", status_code=404)
        all_candidates = sorted(f.name for f in e2_dir.glob("*-2_extract.json"))
        if not all_candidates:
            raise DocumentExtractError("Nenhum extrato E2 encontrado", status_code=404)
        target = _match_by_stored_path(doc, e2_dir) or _match_by_metadata(doc, e2_dir)
        if target is None:
            raise DocumentExtractError(
                "Extrato E2 não encontrado para este documento", status_code=404
            )

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DocumentExtractError(f"Erro ao ler extrato: {exc}", status_code=500) from exc

    return ExtractJsonResult(filename=target.name, data=data, all_candidates=all_candidates)


def _match_irpf_e15a(doc: Document, e2_dir: Path) -> Path | None:
    """Localiza `{stem}-1.5a_extract.json` para um doc IRPF via stored_path."""
    if not doc.stored_path:
        return None
    return _find_e15a_extract(e2_dir, Path(doc.stored_path).name)


def _read_irpf_e15a_from_db(doc: Document, workspace_id: str) -> dict | None:
    """Lê E1.5a direto de ``pipeline_artifacts`` (modo DBArtifactStore).

    Retorna ``{filename, data, all_candidates}`` ou ``None`` se não achar.
    Usa o mesmo stem que `pipeline.stages.e15._artifact_key_for` (strip de
    ``-0_original`` + extensão).
    """
    if not doc.stored_path:
        return None
    stem = _e15a_base_stem(Path(doc.stored_path).name)
    with SyncSessionLocal() as db:
        repo = PipelineArtifactRepository(db)
        art = repo.get_latest_for_workspace(workspace_id, stage="E1.5a", artifact_key=stem)
        if art is None:
            return None
        all_keys = repo.list_latest_keys(workspace_id, stage="E1.5a")
        return {
            "filename": f"{stem}-1.5a_extract.json",
            "data": read_artifact_content(art.content_json),
            "all_candidates": [f"{k}-1.5a_extract.json" for k in all_keys],
        }


def _latest_e2_artifact(repo: PipelineArtifactRepository, workspace_id: str, stem: str):
    """Mais recente de E2-extratos/faturas/llm para um stem (cross-stage)."""
    candidates = (
        repo.get_latest_for_workspace(workspace_id, stage=s, artifact_key=stem)
        for s in _E2_DB_STAGES
    )
    found = [c for c in candidates if c is not None]
    return max(found, key=lambda a: a.created_at) if found else None


def _all_e2_keys(repo: PipelineArtifactRepository, workspace_id: str) -> set[str]:
    """Stems com E2 artifact em qualquer stage do workspace."""
    keys: set[str] = set()
    for stage in _E2_DB_STAGES:
        keys.update(repo.list_latest_keys(workspace_id, stage=stage))
    return keys


def _read_e2_from_db(doc: Document, workspace_id: str) -> dict | None:
    """Lê E2 do DB (DBArtifactStore mode); None se não achar."""
    if not doc.stored_path:
        return None
    stem = _e15a_base_stem(Path(doc.stored_path).name)
    with SyncSessionLocal() as db:
        repo = PipelineArtifactRepository(db)
        latest = _latest_e2_artifact(repo, workspace_id, stem)
        if latest is None:
            return None
        all_keys = _all_e2_keys(repo, workspace_id)
        return {
            "filename": f"{stem}-2_extract.json",
            "data": read_artifact_content(latest.content_json),
            "all_candidates": sorted(f"{k}-2_extract.json" for k in all_keys),
        }


def _match_by_stored_path(doc: Document, e2_dir: Path) -> Path | None:
    """Estratégia 1: correspondência exata via stored_path (mesmo algoritmo do sync)."""
    if not doc.stored_path:
        return None
    source_filename = Path(doc.stored_path).name
    return _find_e2_extract(e2_dir, source_filename)


def _match_by_metadata(doc: Document, e2_dir: Path) -> Path | None:
    """Estratégia 2: fallback por bank_code + doc_type + period."""
    matches = list(e2_dir.glob("*-2_extract.json"))
    if doc.bank_code:
        bank_matches = [f for f in matches if doc.bank_code.lower() in f.name.lower()]
        if bank_matches:
            matches = bank_matches
    # Filtra por tipo de documento antes do período para evitar confusão
    # extrato × fatura.
    if doc.doc_type in _DOC_TYPE_KEYWORDS:
        kws = _DOC_TYPE_KEYWORDS[doc.doc_type]
        type_matches = [f for f in matches if any(kw in f.name.lower() for kw in kws)]
        if type_matches:
            matches = type_matches
    if doc.period:
        period_prefix = doc.period.split("_")[0]
        period_matches = [f for f in matches if period_prefix in f.name]
        if period_matches:
            matches = period_matches
    return sorted(matches)[0] if matches else None
