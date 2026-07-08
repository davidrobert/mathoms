"""Leitura + decryption em batch de ``PasswordVault`` (A6e.4 slice 10).

Extraído de ``api/documents.py`` para remover o uso direto de
``sqlalchemy.select`` no router (gate AST). Consumido por composites
de documents (upload + retry_unlock) que precisam das senhas em texto
puro para destravar PDFs via ``process_uploaded_document``.

Não retorna metadata (hint, created_at…) — só plaintext. Para a API
pública use o use case ``application/vault/list_passwords.py`` que
devolve DTOs com hint mas sem plaintext.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.password_vault import PasswordVault
from backend.app.services.vault import get_vault


async def get_workspace_passwords(workspace_id: str, db: AsyncSession) -> list[str]:
    """Decrypt all vault passwords for a workspace. Retorna ``[]`` se vazio."""
    result = await db.execute(
        select(PasswordVault).where(PasswordVault.workspace_id == workspace_id)
    )
    entries = result.scalars().all()
    if not entries:
        return []
    vault_svc = get_vault()
    passwords: list[str] = []
    for entry in entries:
        plain = vault_svc.decrypt(entry.encrypted_password)
        if plain:
            passwords.append(plain)
    return passwords
