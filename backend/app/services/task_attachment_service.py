"""TaskAttachment service — upload/list/delete anexos de tasks (ADR-074).

Armazena arquivos em `storage/{workspace_id}/task_attachments/{task_id}/`.
A row `task_attachments` referencia o caminho relativo (consistente com
docs/vault do resto do produto). Validação de extensão/tamanho reusa
`StorageService.validate_file`.

Uso típico:
  - Comprovante de quitação (Task #1: financiamento Ed. Gisele)
  - Nota fiscal / DARF
  - Contrato de seguro assinado
  - Print de tela do banco
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.task import TaskAttachment
from backend.app.services import task_service
from backend.app.services.storage import StorageService


_SUBDIR = "task_attachments"


def _attachment_dir(storage: StorageService, workspace_id: str, task_id: str) -> Path:
    return storage.tenant_root(workspace_id) / _SUBDIR / task_id


def _safe_filename(name: str) -> str:
    """Sanitiza filename — evita path traversal + limita tamanho. Reutiliza
    heurística do storage (caminho interno da StorageService). Prefixo '_'
    para nomes que começam com '.'."""
    name = Path(name).name  # strip diretórios
    if not name or name in (".", ".."):
        name = "arquivo"
    if name.startswith("."):
        name = "_" + name
    return name[:255]


async def save_attachment(
    workspace_id: str,
    task_id: str,
    *,
    filename: str,
    content: bytes,
    content_type: Optional[str],
    uploaded_by: Optional[str],
    db: AsyncSession,
) -> TaskAttachment:
    """Salva o arquivo no filesystem + cria row em task_attachments.

    Valida:
    - Task existe no workspace (delegado a task_service.get_task).
    - Extensão permitida + tamanho dentro do limite (StorageService).
    - Sem colisão de nome — se houver, anexa sufixo incremental.
    """
    task = await task_service.get_task(workspace_id, task_id, db=db)

    storage = StorageService()
    ok, error = storage.validate_file(filename, len(content))
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error
        )

    dest_dir = _attachment_dir(storage, workspace_id, task_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    safe = _safe_filename(filename)
    dest = dest_dir / safe
    counter = 1
    while dest.exists():
        stem = Path(safe).stem
        ext = Path(safe).suffix
        dest = dest_dir / f"{stem}_{counter}{ext}"
        counter += 1
    dest.write_bytes(content)

    # Storage path é RELATIVO ao tenant_root — portable entre hosts e não
    # vaza path absoluto no DB.
    rel_path = str(dest.relative_to(storage.tenant_root(workspace_id)))

    attachment = TaskAttachment(
        task_id=task.id,
        workspace_id=workspace_id,
        storage_path=rel_path,
        original_filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        uploaded_by=uploaded_by,
    )
    db.add(attachment)
    await db.flush()
    return attachment


async def list_attachments(
    workspace_id: str,
    task_id: str,
    *,
    db: AsyncSession,
) -> list[TaskAttachment]:
    """Lista anexos de uma task. Valida que task pertence ao workspace."""
    await task_service.get_task(workspace_id, task_id, db=db)
    stmt = (
        select(TaskAttachment)
        .where(
            TaskAttachment.workspace_id == workspace_id,
            TaskAttachment.task_id == task_id,
        )
        .order_by(TaskAttachment.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_attachment(
    workspace_id: str,
    attachment_id: str,
    *,
    db: AsyncSession,
) -> TaskAttachment:
    """Retorna row de anexo (com tenancy check)."""
    stmt = select(TaskAttachment).where(
        TaskAttachment.workspace_id == workspace_id,
        TaskAttachment.id == attachment_id,
    )
    result = await db.execute(stmt)
    attachment = result.scalar_one_or_none()
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anexo não encontrado",
        )
    return attachment


async def delete_attachment(
    workspace_id: str,
    attachment_id: str,
    *,
    db: AsyncSession,
) -> None:
    """Remove anexo (row + arquivo). Idempotente: arquivo ausente no disco
    não impede remoção da row."""
    attachment = await get_attachment(workspace_id, attachment_id, db=db)
    storage = StorageService()
    resolved = storage.resolve_path(workspace_id, attachment.storage_path)
    if resolved is not None and resolved.is_file():
        try:
            resolved.unlink()
        except OSError:
            # Log em ambiente produtivo — aqui preferimos completar a remoção da row
            pass

    await db.delete(attachment)
    await db.flush()


def resolve_attachment_file(
    workspace_id: str,
    attachment: TaskAttachment,
) -> Optional[Path]:
    """Resolve o Path absoluto do anexo com proteção contra traversal.
    Usado pelo endpoint de download."""
    storage = StorageService()
    return storage.resolve_path(workspace_id, attachment.storage_path)


__all__ = [
    "save_attachment",
    "list_attachments",
    "get_attachment",
    "delete_attachment",
    "resolve_attachment_file",
]
