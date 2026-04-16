"""Invitation service — F9 · workspace sharing.

Gerencia o ciclo de vida de `WorkspaceInvitation`:

  - `create_invitation`   — owner convida por email + role
  - `list_invitations`    — lista convites de um workspace (com status)
  - `revoke_invitation`   — owner cancela antes do aceite
  - `get_by_token`        — resolve convite pelo token cru (para preview e aceite)
  - `accept_invitation`   — convidado transforma convite em `WorkspaceMember`

Regras invariantes:

1. Token cru existe apenas no retorno de `create_invitation` e no link.
   No DB guardamos só `sha256(token)`.
2. Aceite cria `WorkspaceMember` na mesma transação. Se constraint
   `uq_workspace_member` falhar (user já é membro), aceite retorna o
   membership existente e marca o convite como `accepted_at` mesmo assim
   — idempotência defensiva.
3. Convite expirado/revogado/aceito é terminal: `accept` levanta 410 Gone.
4. Rate limit: no máximo `MAX_PENDING_PER_WORKSPACE` convites pendentes
   por workspace. Stateful rate limit (não por IP) — ADR-072 assume que
   o abuso é dentro do tenant, não cross-tenant.

Erros:

    InvitationError: subclasse de ValueError, levantada em regra de negócio
                     (expirado, já aceito, role inválida, email já é membro,
                     limite atingido). API traduz para 4xx apropriado.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.workspace_invitation import WorkspaceInvitation
from backend.app.models.workspace_member import VALID_ROLES, WorkspaceMember


# ─── Configuração ──────────────────────────────────────────────────────

INVITATION_TTL = timedelta(hours=72)
MAX_PENDING_PER_WORKSPACE = 10
TOKEN_BYTES = 32  # 256 bits → 43 chars URL-safe base64


class InvitationError(ValueError):
    """Erro de regra de negócio em convite. API traduz para HTTP 4xx."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


# ─── Token helpers ─────────────────────────────────────────────────────


def _hash_token(raw: str) -> str:
    """SHA-256 hex. Não usamos HMAC porque o token já é aleatório 256-bit —
    o hash serve só pra evitar que leak de DB dê convites prontos."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _generate_token() -> tuple[str, str]:
    """Retorna `(raw, hash)`. Raw é URL-safe, pode ir direto na URL."""
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    return raw, _hash_token(raw)


# ─── Create ────────────────────────────────────────────────────────────


async def create_invitation(
    workspace_id: str,
    *,
    email: str,
    role: str,
    invited_by: str,
    db: AsyncSession,
) -> tuple[WorkspaceInvitation, str]:
    """Cria um convite pendente. Retorna `(invitation, raw_token)` — o
    caller deve devolver `raw_token` ao cliente e NÃO persistir em outro
    lugar.

    Raises:
        InvitationError:
            - `invalid_role`     — role fora de VALID_ROLES
            - `already_member`   — user com esse email já é membro
            - `limit_reached`    — workspace atingiu MAX_PENDING_PER_WORKSPACE
    """
    role = role.strip()
    email = email.strip().lower()

    if role not in VALID_ROLES:
        raise InvitationError("invalid_role", f"Papel inválido: {role}")

    # Owner só pode ser atribuído na criação do workspace — não por convite.
    if role == "owner":
        raise InvitationError(
            "invalid_role",
            "Não é possível convidar um novo owner. Transferência de "
            "ownership é uma ação separada (não disponível ainda).",
        )

    # Já é membro? Olhamos via join user.email → workspace_members.
    existing_member = await db.execute(
        select(WorkspaceMember)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            func.lower(User.email) == email,
        )
    )
    if existing_member.scalar_one_or_none() is not None:
        raise InvitationError(
            "already_member",
            f"{email} já é membro deste workspace.",
        )

    # Rate limit de pendentes.
    now = datetime.now(timezone.utc)
    pending_count = await _count_pending(db, workspace_id=workspace_id, now=now)
    if pending_count >= MAX_PENDING_PER_WORKSPACE:
        raise InvitationError(
            "limit_reached",
            f"Limite de {MAX_PENDING_PER_WORKSPACE} convites pendentes atingido.",
        )

    raw, token_hash = _generate_token()

    invitation = WorkspaceInvitation(
        workspace_id=workspace_id,
        email=email,
        role=role,
        token_hash=token_hash,
        invited_by=invited_by,
        expires_at=now + INVITATION_TTL,
    )
    db.add(invitation)
    await db.flush()
    return invitation, raw


async def _count_pending(
    db: AsyncSession, *, workspace_id: str, now: datetime
) -> int:
    """Conta convites em estado `pending` (não aceito, não revogado, não expirado)."""
    stmt = (
        select(func.count())
        .select_from(WorkspaceInvitation)
        .where(
            WorkspaceInvitation.workspace_id == workspace_id,
            WorkspaceInvitation.accepted_at.is_(None),
            WorkspaceInvitation.revoked_at.is_(None),
            WorkspaceInvitation.expires_at > now,
        )
    )
    result = await db.execute(stmt)
    return int(result.scalar_one())


# ─── List ──────────────────────────────────────────────────────────────


async def list_invitations(
    workspace_id: str,
    *,
    include_terminal: bool = True,
    db: AsyncSession,
) -> list[WorkspaceInvitation]:
    """Lista convites do workspace, mais recentes primeiro.

    `include_terminal=False` filtra apenas pendentes válidos.
    """
    stmt = select(WorkspaceInvitation).where(
        WorkspaceInvitation.workspace_id == workspace_id,
    )
    if not include_terminal:
        now = datetime.now(timezone.utc)
        stmt = stmt.where(
            WorkspaceInvitation.accepted_at.is_(None),
            WorkspaceInvitation.revoked_at.is_(None),
            WorkspaceInvitation.expires_at > now,
        )
    stmt = stmt.order_by(WorkspaceInvitation.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ─── Revoke ────────────────────────────────────────────────────────────


async def revoke_invitation(
    workspace_id: str,
    invitation_id: str,
    *,
    db: AsyncSession,
) -> WorkspaceInvitation:
    """Marca `revoked_at = now`. Idempotente: revogar convite já revogado
    é no-op. Revogar convite já aceito levanta `InvitationError`."""
    stmt = select(WorkspaceInvitation).where(
        WorkspaceInvitation.workspace_id == workspace_id,
        WorkspaceInvitation.id == invitation_id,
    )
    result = await db.execute(stmt)
    inv = result.scalar_one_or_none()
    if inv is None:
        raise InvitationError("not_found", "Convite não encontrado.")
    if inv.accepted_at is not None:
        raise InvitationError(
            "already_accepted",
            "Convite já foi aceito — remova o membro em vez de revogar.",
        )
    if inv.revoked_at is None:
        inv.revoked_at = datetime.now(timezone.utc)
        db.add(inv)
        await db.flush()
    return inv


# ─── Accept ────────────────────────────────────────────────────────────


async def get_by_token(
    raw_token: str,
    *,
    db: AsyncSession,
) -> Optional[WorkspaceInvitation]:
    """Resolve convite pelo token cru. Retorna None se não encontrado.

    Esta é a única query de convite que **não** filtra por `workspace_id` —
    o token É o vetor de autenticação.
    """
    token_hash = _hash_token(raw_token)
    # tenancy: global — token lookup é auth-level, workspace_id vem do convite
    stmt = select(WorkspaceInvitation).where(
        WorkspaceInvitation.token_hash == token_hash
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def accept_invitation(
    raw_token: str,
    *,
    acceptor: User,
    db: AsyncSession,
) -> WorkspaceMember:
    """Aceita o convite. Cria `WorkspaceMember` e marca `accepted_at`.

    - O email do convite DEVE bater com o email do `acceptor` (case-insensitive).
    - Se já for membro (por outro fluxo), marca aceite mesmo assim e retorna
      o membership existente (idempotência).

    Raises:
        InvitationError:
            - `not_found`      — token inválido
            - `expired`        — TTL passou
            - `revoked`        — revogado pelo owner
            - `already_accepted` — já aceito
            - `email_mismatch` — convite é para outro email
    """
    inv = await get_by_token(raw_token, db=db)
    if inv is None:
        raise InvitationError("not_found", "Convite não encontrado ou token inválido.")

    if inv.revoked_at is not None:
        raise InvitationError("revoked", "Este convite foi revogado.")
    if inv.accepted_at is not None:
        raise InvitationError("already_accepted", "Este convite já foi aceito.")

    now = datetime.now(timezone.utc)
    exp = inv.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp <= now:
        raise InvitationError("expired", "Este convite expirou.")

    if acceptor.email.strip().lower() != inv.email.strip().lower():
        raise InvitationError(
            "email_mismatch",
            "Este convite é para outro email. Entre com a conta certa.",
        )

    # Cria membership (ou reutiliza se já existe — idempotência).
    # tenancy: global — lookup by (workspace_id, user_id) é ws-scoped,
    # mas não envolve `workspace_id` no .where explícito porque pegamos
    # pelo invite (já com ws scope). Para o lint, adicionamos abaixo:
    existing = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == inv.workspace_id,
            WorkspaceMember.user_id == acceptor.id,
        )
    )
    member = existing.scalar_one_or_none()
    if member is None:
        member = WorkspaceMember(
            workspace_id=inv.workspace_id,
            user_id=acceptor.id,
            role=inv.role,
            invited_by=inv.invited_by,
        )
        db.add(member)
        await db.flush()

    inv.accepted_at = now
    inv.accepted_by_user_id = acceptor.id
    db.add(inv)
    await db.flush()
    return member


__all__ = [
    "InvitationError",
    "INVITATION_TTL",
    "MAX_PENDING_PER_WORKSPACE",
    "create_invitation",
    "list_invitations",
    "revoke_invitation",
    "get_by_token",
    "accept_invitation",
]
