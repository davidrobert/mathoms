"""Composite: retry unlock em lote para docs ``needs_password`` (A6e.4 slice 10).

Extraído de ``api/documents.py::retry_unlock``. Re-roda o
``process_uploaded_document`` com o conjunto atual de senhas do vault
em cada doc travado — cobre o caso em que o usuário adicionou a senha
certa depois do upload.

Não commita; router decide transação + audit.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.document import Document, DocumentStatus
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.services.documents.document_processor import process_uploaded_document
from backend.app.services.security.password_vault_reader import get_workspace_passwords
from backend.app.services.storage import StorageService


class RetryUnlockError(Exception):
    """Pré-condições falhadas (sem senhas, sem docs travados). Router → 400/404."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class RetryUnlockStats:
    total_attempted: int
    total_ready: int
    total_errored: int


async def retry_unlock_workspace_documents(
    workspace_id: str,
    *,
    db: AsyncSession,
    repo: DocumentRepository,
    storage: StorageService,
) -> tuple[list[Document], RetryUnlockStats]:
    """Retorna ``(updated_docs, stats)``. Caller comita + faz refresh."""
    passwords = await get_workspace_passwords(workspace_id, db)
    if not passwords:
        raise RetryUnlockError("Nenhuma senha cadastrada no vault", status_code=400)

    docs = await repo.list(workspace_id, statuses=[DocumentStatus.needs_password])
    if not docs:
        raise RetryUnlockError("Nenhum documento pendente de senha", status_code=404)

    config_dir = settings.PIPELINE_ROOT / "config"
    tenant_root = storage.ensure_tenant_dirs(workspace_id)

    for doc in docs:
        _retry_single(
            doc,
            passwords=passwords,
            config_dir=config_dir,
            tenant_root=tenant_root,
            workspace_id=workspace_id,
            storage=storage,
        )

    stats = RetryUnlockStats(
        total_attempted=len(docs),
        total_ready=sum(1 for d in docs if d.status == DocumentStatus.ready),
        total_errored=sum(1 for d in docs if d.status == DocumentStatus.error),
    )
    return docs, stats


def _retry_single(
    doc: Document,
    *,
    passwords: list[str],
    config_dir,
    tenant_root,
    workspace_id: str,
    storage: StorageService,
) -> None:
    abs_doc = storage.abs_stored_file(workspace_id, doc.stored_path)
    if not doc.stored_path or not abs_doc or not abs_doc.exists():
        doc.status = DocumentStatus.error
        doc.error_message = "Arquivo não encontrado no storage"
        return

    try:
        result = process_uploaded_document(
            abs_doc,
            passwords,
            config_dir,
            tenant_root=tenant_root,
            workspace_id=workspace_id,
            content_hash=doc.content_hash,
        )
    except Exception as exc:
        doc.status = DocumentStatus.error
        doc.error_message = f"Erro no retry: {str(exc)[:500]}"
        return

    doc.status = result["status"]
    doc.doc_type = result["doc_type"]
    doc.bank_code = result["bank_code"]
    doc.period = result["period"]
    doc.classification_meta = result["classification_meta"]
    doc.error_message = result["error_message"]
    rel = result.get("stored_path_relative")
    if rel:
        doc.stored_path = rel
