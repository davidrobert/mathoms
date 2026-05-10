"""Mapper ORM → DTO para o agregado ``Document``.

O mapper **não** recebe ``AsyncSession``. Recebe a instância ORM já
hidratada — isso torna o mapper testável sem DB.

Regra dos enums: ``Document.doc_type`` e ``Document.status`` são
``sqlalchemy.Enum`` — no identity map vêm sempre como instâncias do enum
Python. O DTO é declarado em cima dos mesmos enums, então ``model_validate``
aceita a instância diretamente. Não precisamos de ``.value``.
"""

from __future__ import annotations

from backend.app.models.document import Document
from backend.app.schemas.dto.document.response import DocumentResponse


def document_to_response(document: Document) -> DocumentResponse:
    """Converte ORM ``Document`` → DTO de resposta. Deriva ``e0_doc_type`` do meta."""
    response = DocumentResponse.model_validate(document)
    response.e0_doc_type = _extract_e0_doc_type(document.classification_meta)
    return response


def _extract_e0_doc_type(meta: dict | None) -> str | None:
    """Lê o subtipo (E0 code) do ``classification_meta``.

    Hierarquia: ``content.doc_type`` (regex) tem precedência sobre ``llm.doc_type``
    (LLM fallback). Sem column dedicada no DB para evitar migration; meta é JSON
    populado por ``classify_document``.
    """
    if not meta:
        return None
    content = meta.get("content")
    if isinstance(content, dict) and content.get("doc_type"):
        return str(content["doc_type"])
    llm = meta.get("llm")
    if isinstance(llm, dict) and llm.get("doc_type"):
        return str(llm["doc_type"])
    return None
