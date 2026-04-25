"""Seed service — bootstrap do usuário admin para primeiro login."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.models.workspace import Workspace


async def ensure_seed_user(db: AsyncSession) -> tuple[User, Workspace]:
    """Get or create the default seed user + workspace for first login."""
    from backend.app.core.security import hash_password

    result = await db.execute(select(User).where(User.email == "admin@mathoms.ai"))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email="admin@mathoms.ai",
            hashed_password=hash_password("admin"),
            full_name="Admin (Seed)",
        )
        db.add(user)
        await db.flush()

        ws = Workspace(name="Workspace Principal", owner_id=user.id)
        db.add(ws)
        await db.commit()
        await db.refresh(user)
    else:
        ws_result = await db.execute(select(Workspace).where(Workspace.owner_id == user.id))
        ws = ws_result.scalar_one_or_none()

    return user, ws
