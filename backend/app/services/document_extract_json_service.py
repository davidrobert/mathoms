"""Composite: lê o extrato E2 (JSON) de um documento (A6e.4 slice 10).

Extraído de ``api/documents.py::get_document_extract_json`` (endpoint
de debug/dev). Estratégias de match (stored_path exato → bank_code +
doc_type + period) seguem paridade com `document_pipeline_sync`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.app.models.document import Document, DocumentType
from backend.app.services.document_pipeline_sync import _find_e2_extract
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
    if not e2_dir.exists():
        raise DocumentExtractError("Nenhum extrato E2 disponível", status_code=404)

    all_candidates = sorted(f.name for f in e2_dir.glob("*-2_extract.json"))
    if not all_candidates:
        raise DocumentExtractError("Nenhum extrato E2 encontrado", status_code=404)

    target = _match_by_stored_path(doc, e2_dir) or _match_by_metadata(doc, e2_dir)
    if target is None:
        raise DocumentExtractError("Extrato E2 não encontrado para este documento", status_code=404)

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DocumentExtractError(f"Erro ao ler extrato: {exc}", status_code=500) from exc

    return ExtractJsonResult(filename=target.name, data=data, all_candidates=all_candidates)


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
