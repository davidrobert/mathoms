"""seed_smoke.py — Seed para ambiente de smoke test (A6b.5.2).

Cria dois usuários com workspaces distintos e copia fixtures do
``tests/fixtures/smoke_inbox/`` para o inbox de cada workspace.

Idempotente: re-rodar não duplica dados.

Usage:
    python backend/app/scripts/seed_smoke.py [--force]

    --force  Apaga usuários existentes e recria (útil após smoke-reset).

Credenciais criadas:
    smoke@mathoms.ai   / smoke123   → workspace "Smoke Premium"  (tier premium simulado)
    viewer@mathoms.ai  / viewer123  → workspace "Smoke Free"     (tier free, sem LLM)
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import async_session, init_db
from backend.app.core.security import hash_password
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.workspace_member import WorkspaceMember

SMOKE_FIXTURES_DIR = _PROJECT_ROOT / "tests" / "fixtures" / "smoke_inbox"

_USERS = [
    {
        "email": "smoke@mathoms.ai",
        "password": "smoke123",
        "full_name": "Smoke Admin",
        "workspace_name": "Smoke Premium",
    },
    {
        "email": "viewer@mathoms.ai",
        "password": "viewer123",
        "full_name": "Viewer Free",
        "workspace_name": "Smoke Free",
    },
]


def _copy_fixtures_to_inbox(workspace_id: str) -> list[str]:
    """Copia todos os fixtures de smoke_inbox para storage/<ws_id>/inbox/."""
    if not SMOKE_FIXTURES_DIR.exists():
        return []

    inbox = Path(settings.STORAGE_ROOT) / workspace_id / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    copied = []
    for fpath in sorted(SMOKE_FIXTURES_DIR.rglob("*")):
        if fpath.is_file() and not fpath.name.startswith(".") and fpath.name != "README.md":
            dest = inbox / fpath.name
            if not dest.exists():
                shutil.copy2(fpath, dest)
                copied.append(fpath.name)

    return copied


async def _ensure_user_workspace(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    workspace_name: str,
    force: bool,
) -> tuple[User, Workspace, bool]:
    """Get or create user + workspace. Returns (user, workspace, created)."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user and force:
        await db.delete(user)
        await db.flush()
        user = None

    created = False
    if user is None:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        db.add(user)
        await db.flush()
        created = True

    # Workspace
    result = await db.execute(
        select(Workspace).where(
            Workspace.owner_id == user.id,
            Workspace.deleted_at.is_(None),
        )
    )
    ws = result.scalar_one_or_none()

    if ws is None:
        ws = Workspace(
            id=str(uuid.uuid4()),
            name=workspace_name,
            owner_id=user.id,
        )
        db.add(ws)
        await db.flush()

        # ADR-072: owner precisa de linha em workspace_members
        db.add(
            WorkspaceMember(
                id=str(uuid.uuid4()),
                workspace_id=ws.id,
                user_id=user.id,
                role="owner",
            )
        )
        await db.flush()
        created = True

    return user, ws, created


async def main(force: bool = False) -> None:
    await init_db()
    print("=" * 60)
    print("  Mathoms AI — Smoke Seed")
    print("=" * 60)

    async with async_session() as db:
        for spec in _USERS:
            user, ws, created = await _ensure_user_workspace(
                db,
                email=spec["email"],
                password=spec["password"],
                full_name=spec["full_name"],
                workspace_name=spec["workspace_name"],
                force=force,
            )
            label = "CRIADO" if created else "JÁ EXISTE"
            print(f"  [{label}] {spec['email']} → workspace {ws.name} (id: {ws.id[:8]}…)")

            if created or force:
                copied = _copy_fixtures_to_inbox(ws.id)
                if copied:
                    print(f"    Inbox: {len(copied)} fixture(s) copiado(s)")
                    for name in copied:
                        print(f"      + {name}")
                elif not SMOKE_FIXTURES_DIR.exists():
                    print(f"    ⚠  Fixtures não encontrados em {SMOKE_FIXTURES_DIR}")
                else:
                    print(f"    Inbox: já populado (sem novos arquivos)")

        await db.commit()

    print()
    print("  Credenciais:")
    for spec in _USERS:
        print(f"    {spec['email']:30s}  /  {spec['password']}")
    print()
    print("  URL: http://localhost:3000")
    print("  API: http://localhost:8000")
    print("  Docs: http://localhost:8000/api/docs")
    print()
    print("  Próximo passo: abra http://localhost:3000 e faça login.")
    print("  Consulte docs/SMOKE_TEST_HUMAN.md para o checklist completo.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Recriar usuários existentes")
    args = parser.parse_args()
    asyncio.run(main(force=args.force))
