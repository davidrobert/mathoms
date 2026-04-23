"""Toggle is_developer flag em um usuário (por email).

Ops-only. Gating de features internas (ex.: "Reclassificar Despesas") que
devem aparecer apenas para contas dev.

Usage:
    .venv/bin/python -m backend.app.scripts.set_developer_flag <email> --enable
    .venv/bin/python -m backend.app.scripts.set_developer_flag <email> --disable
    .venv/bin/python -m backend.app.scripts.set_developer_flag --list
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.user import User


async def _set_flag(email: str, value: bool) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"error: user not found: {email}", file=sys.stderr)
            return 1
        if user.is_developer == value:
            print(f"noop: {email} is_developer already {value}")
            return 0
        user.is_developer = value
        await db.commit()
        print(f"ok: {email} is_developer={value}")
        return 0


async def _list_devs() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User.email, User.full_name).where(User.is_developer.is_(True))
        )
        rows = result.all()
        if not rows:
            print("no developer accounts")
            return 0
        for email, name in rows:
            print(f"{email}\t{name}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", nargs="?", help="User email")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--enable", action="store_true", help="Set is_developer=True")
    group.add_argument("--disable", action="store_true", help="Set is_developer=False")
    group.add_argument("--list", action="store_true", help="List developer accounts")
    args = parser.parse_args()

    if args.list:
        return asyncio.run(_list_devs())
    if not args.email or not (args.enable or args.disable):
        parser.error("provide <email> with --enable or --disable, or use --list")
    return asyncio.run(_set_flag(args.email, args.enable))


if __name__ == "__main__":
    sys.exit(main())
