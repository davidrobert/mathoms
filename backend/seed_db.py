#!/usr/bin/env python3
"""Seed the database with existing pipeline reports.

Usage:
    python -m backend.seed_db
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.database import async_session, init_db
from backend.app.services.seed import ensure_seed_user, seed_existing_reports


async def main():
    print("=" * 60)
    print("  Mathoms AI — Database Seed")
    print("=" * 60)

    await init_db()
    print("  [OK] Database initialized")

    async with async_session() as db:
        user, ws = await ensure_seed_user(db)
        print(f"  [OK] Seed user: {user.email} (id: {user.id})")
        print(f"  [OK] Workspace: {ws.name} (id: {ws.id})")

        imported = await seed_existing_reports(db, user.id, ws.id)
        if imported:
            for r in imported:
                print(f"  [+] Imported: {r['title']} ({r['size'] / 1024:.0f}KB)")
        else:
            print("  [INFO] No new reports to import")

    print("=" * 60)
    print("  Seed complete!")
    print("  Login: admin@mathoms.ai / admin")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
