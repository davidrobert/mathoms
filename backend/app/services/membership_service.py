"""Membership service — F9 · gestão de membros existentes.

Operações:

  - `list_members`       — listagem para a página "Membros"
  - `update_member_role` — muda o role de um membro (owner-only)
  - `remove_member`      — remove um membro do workspace (owner-only)

Regras:

1. Não é possível mudar o role de um `owner`. Transferência de
   ownership não é coberta no V1 (débito explícito).
2. Não é possível remover o próprio owner. A API devolve 409 Conflict
   nesse caso — o frontend deve direcionar para "deletar workspace"
   (fluxo diferente).
3. Role alvo precisa estar em `VALID_ROLES` e ser diferente de `owner`.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.models.workspace import Workspace  # noqa: F401 — typing/import parity
from backend.app.models.workspace_member import VALID_ROLES, WorkspaceMember


class MembershipError(ValueError):
    """Erro de regra de negócio em membership. API traduz para HTTP 4xx."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


async def list_members(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> list[tuple[WorkspaceMember, User]]:
    """Lista (WorkspaceMember, User) de um workspace, ordenado por
    joined_at asc (owner primeiro na prática)."""
    stmt = (
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.joined_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.all())


async def get_member(
    workspace_id: str,
    user_id: str,
    *,
    db: AsyncSession,
) -> Optional[WorkspaceMember]:
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_member_role(
    workspace_id: str,
    user_id: str,
    *,
    new_role: str,
    db: AsyncSession,
) -> WorkspaceMember:
    """Atualiza o role. Raises `MembershipError` se:
      - member não existe no workspace
      - new_role é `owner` ou inválido
      - member é o owner do workspace
    """
    new_role = new_role.strip()
    if new_role not in VALID_ROLES:
        raise MembershipError("invalid_role", f"Papel inválido: {new_role}")
    if new_role == "owner":
        raise MembershipError(
            "invalid_role",
            "Não é possível promover para owner via troca de role. "
            "Transferência de ownership é fluxo separado.",
        )

    member = await get_member(workspace_id, user_id, db=db)
    if member is None:
        raise MembershipError("not_found", "Membro não encontrado.")
    if member.role == "owner":
        raise MembershipError(
            "is_owner",
            "Não é possível mudar o role do owner. Use transferência de ownership.",
        )

    member.role = new_role
    db.add(member)
    await db.flush()
    return member


async def remove_member(
    workspace_id: str,
    user_id: str,
    *,
    db: AsyncSession,
) -> WorkspaceMember:
    """Remove o member do workspace e invalida todas as sessões do user.

    F9.2 · forced logout — incrementamos `User.token_version`, o que faz
    qualquer JWT emitido antes desta operação ser rejeitado por
    `get_current_user`. O user removido precisa fazer login de novo; se
    ainda for membro de outros workspaces, continua tendo acesso a eles
    após o novo login.

    Levanta `MembershipError` se:
      - member não existe
      - member é o owner (precisaria transferir ownership primeiro)
    """
    member = await get_member(workspace_id, user_id, db=db)
    if member is None:
        raise MembershipError("not_found", "Membro não encontrado.")
    if member.role == "owner":
        raise MembershipError(
            "is_owner",
            "Não é possível remover o owner do próprio workspace.",
        )

    # Bump token_version ANTES do delete — se falhar o delete, a bumpada
    # fica dentro da mesma transação e sofre rollback junto.
    # tenancy: global — User é auth-level, não tenant-scoped.
    user_row = await db.execute(select(User).where(User.id == user_id))
    target_user = user_row.scalar_one_or_none()
    if target_user is not None:
        target_user.token_version = (target_user.token_version or 0) + 1
        db.add(target_user)

    await db.delete(member)
    await db.flush()
    return member


__all__ = [
    "MembershipError",
    "list_members",
    "get_member",
    "update_member_role",
    "remove_member",
]
