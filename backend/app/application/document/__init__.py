"""Use cases do agregado ``Document`` (ADR-101 R15 · ADR-081).

Endpoints clean de ``/workspaces/{id}/documents/*`` delegam aqui:
- ``list_workspace_documents`` — GET ``/documents``
- ``get_document`` — suporte para GET ``/documents/{id}/file`` e
  ``/extract-json`` (ambos continuam no router por serem composite de
  storage/filesystem)
- ``update_document_classification`` — PATCH ``/documents/{id}``
- ``delete_document`` — DELETE ``/documents/{id}`` (repo only; arquivo
  em disco permanece no router/StorageService)
- ``list_duplicate_candidates`` — listagem fuzzy (ADR-081)
- ``reclassify_document`` — por doc único; chamado pelo bulk router

Deferred ao router por serem composites multicamada (storage + audit +
pipeline + validação cruzada, ADR-112 rollback):
- ``POST /upload`` — orquestra storage, classify, audit, fuzzy dedup,
  IntegrityError handling
- ``POST /retry-unlock`` — bulk storage + classify + audit
- ``GET /{id}/file`` — FileResponse + ``Content-Disposition`` + cache
- ``GET /{id}/extract-json`` — filesystem scan em ``E2_extracts/``
- ``POST /reclassify`` — bulk threadpool + rename canônico + audit

``ClassificationServiceProtocol`` desacopla o LLM/regex side-effect
(``document_classification.classify_document``) para que tests rodem
sem LLM real.
"""

from backend.app.application.document.delete_document import delete_document
from backend.app.application.document.get_document import get_document
from backend.app.application.document.list_duplicate_candidates import (
    list_duplicate_candidates,
)
from backend.app.application.document.list_workspace_documents import (
    list_workspace_documents,
)
from backend.app.application.document.reclassify_document import (
    reclassify_document,
)
from backend.app.application.document.update_document_classification import (
    update_document_classification,
)

__all__ = [
    "delete_document",
    "get_document",
    "list_duplicate_candidates",
    "list_workspace_documents",
    "reclassify_document",
    "update_document_classification",
]
