"""Use case: cria user + workspace + WorkspaceMember(owner)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.auth.login_user import issue_session_tokens
from backend.app.application.base import ConflictError
from backend.app.core.security import hash_password
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.workspace_member import WorkspaceMember
from backend.app.schemas.auth import RegisterRequest, SessionTokens


async def register_user(body: RegisterRequest, *, db: AsyncSession) -> SessionTokens:
    if await _email_exists(body.email, db=db):
        raise ConflictError("Email já cadastrado")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()

    workspace = Workspace(name=f"Workspace de {body.full_name}", owner_id=user.id)
    db.add(workspace)
    await db.flush()

    # ADR-072: acesso ao tenant exige linha em workspace_members
    # (owner_id sozinho não basta).
    db.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
        )
    )
    await db.commit()
    await db.refresh(user)

    return await issue_session_tokens(user, db=db)


async def _email_exists(email: str, *, db: AsyncSession) -> bool:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none() is not None
