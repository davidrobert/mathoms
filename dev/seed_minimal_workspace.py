#!/usr/bin/env python3
"""Seed idempotente de um workspace mínimo para dev local em Docker (A20.L6)."""

# Rodado pelo `entrypoint.dev.sh` no boot do container `api` quando o DB está
# vazio. Cria User + Workspace + WorkspaceMember (owner) + 2 FamilyMembers
# sintéticos. Idempotente em dois níveis: short-circuit por count() e
# get-or-create por e-mail — re-run num DB já seedado é no-op silencioso.
# Dados são 100% sintéticos (ADR sobre dados sensíveis): nenhum CPF/valor real.

import asyncio

from sqlalchemy import func, select

from backend.app.core.database import async_session
from backend.app.core.security import hash_password
from backend.app.models.family_member import FamilyMember
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.workspace_member import WorkspaceMember

SEED_EMAIL = "dev@mathoms.local"
SEED_PASSWORD = "devpassword"
_MEMBERS = (
    {
        "key": "titular",
        "full_name": "Dev Titular",
        "short_name": "Titular",
        "role": "titular",
        "order": 0,
    },
    {
        "key": "conjuge",
        "full_name": "Dev Cônjuge",
        "short_name": "Cônjuge",
        "role": "titular",
        "order": 1,
    },
)


async def _get_or_create_user(db) -> User:
    """Retorna o user seed, criando-o se ainda não existir."""
    existing = (await db.execute(select(User).where(User.email == SEED_EMAIL))).scalar_one_or_none()
    if existing:
        return existing
    user = User(
        email=SEED_EMAIL, hashed_password=hash_password(SEED_PASSWORD), full_name="Dev Local"
    )
    db.add(user)
    await db.flush()
    return user


def _build_members(workspace_id: str) -> list[FamilyMember]:
    """Constrói os FamilyMembers sintéticos para o workspace."""
    return [FamilyMember(workspace_id=workspace_id, **m) for m in _MEMBERS]


async def _seed(db) -> None:
    """Cria workspace + membership + family_members num DB vazio."""
    user = await _get_or_create_user(db)
    workspace = Workspace(name="Workspace Dev", family_surname="Dev", owner_id=user.id)
    db.add(workspace)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    db.add_all(_build_members(workspace.id))
    await db.commit()


async def main() -> None:
    """Short-circuit por count(); seed só quando não há nenhum workspace."""
    async with async_session() as db:
        count = (await db.execute(select(func.count()).select_from(Workspace))).scalar_one()
        if count:
            print(f"[seed] {count} workspace(s) já presente(s) — skip")
            return
        await _seed(db)
        print(f"[seed] workspace mínimo criado (login: {SEED_EMAIL} / {SEED_PASSWORD})")


if __name__ == "__main__":
    asyncio.run(main())
