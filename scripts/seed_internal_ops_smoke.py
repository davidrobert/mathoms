"""Seed mínimo para smoke test do console interno (F7F-Local Slice 3).

Cria 1 user fixture (email + senha fixos) no DB corrente. Usado por
Playwright `@internal-ops` via `PW_FIXTURE_USER_ID` e pelo smoke manual.

Uso:
    MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(pwd)/mathoms-smoke.db" \\
        python3 scripts/seed_internal_ops_smoke.py

Imprime o `user_id` no stdout (única linha) para caller capturar.
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import async_session
from backend.app.core.security import hash_password
from backend.app.models.user import User

FIXTURE_EMAIL = "smoke-fixture@mathoms.dev"
FIXTURE_FULLNAME = "Smoke Fixture"
FIXTURE_PASSWORD = "SmokeFixture123!"


async def _seed(db: AsyncSession) -> str:
    existing = (
        await db.execute(select(User).where(User.email == FIXTURE_EMAIL))
    ).scalar_one_or_none()
    if existing is not None:
        return existing.id
    u = User(
        email=FIXTURE_EMAIL,
        full_name=FIXTURE_FULLNAME,
        hashed_password=hash_password(FIXTURE_PASSWORD),
        is_active=True,
    )
    db.add(u)
    await db.flush()
    await db.commit()
    return u.id


async def main() -> None:
    async with async_session() as db:
        user_id = await _seed(db)
        sys.stdout.write(user_id + "\n")


if __name__ == "__main__":
    asyncio.run(main())
