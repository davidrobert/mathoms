"""Reset completo da plataforma (dev/staging): apaga todos os utilizadores e dados
em cascata, limpa ``storage/`` e opcionalmente faz flush do Redis (broker Celery).

**Irreversível.** Use sempre ``--dry-run`` antes de ``--apply``.

Com ``--apply``, o script exige **duas confirmações interativas** (frases exactas)
antes de executar qualquer operação destrutiva.

Passos (com ``--apply``):
    1. ``DELETE FROM users`` (cascata para workspaces, documentos, relatórios, etc.)
    2. Remover todo o conteúdo de ``STORAGE_ROOT`` (directórios por tenant)
    3. Opcional: ``FLUSHDB`` no Redis apontado por ``MATHOMS_REDIS_URL``

Usage:
    .venv/bin/python -m backend.app.scripts.reset_platform --dry-run
    .venv/bin/python -m backend.app.scripts.reset_platform --apply
    .venv/bin/python -m backend.app.scripts.reset_platform --apply --skip-redis
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.user import User
from backend.app.models.workspace import Workspace

CONFIRM_PHRASE_1 = "DELETE ALL DATA"
CONFIRM_PHRASE_2 = "RESET PLATFORM IRREVERSIBLE"


def _is_sqlite(url: str) -> bool:
    return url.startswith(("sqlite:///", "sqlite+aiosqlite:///", "sqlite+pysqlite:///"))


def _redact_database_url(url: str) -> str:
    """Oculta password em URLs tipo ``scheme://user:pass@host``."""
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    creds, hostpart = rest.rsplit("@", 1)
    if ":" not in creds:
        return url
    user, _sep, _pw = creds.partition(":")
    return f"{scheme}://{user}:***@{hostpart}"


def _storage_root() -> Path:
    return Path(settings.STORAGE_ROOT).resolve()


def _du(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _prompt_exact(label: str, expected: str) -> bool:
    print(f"\n{label}", flush=True)
    print(f"  (escreva exactamente: {expected!r})", flush=True)
    try:
        line = input("> ").strip()
    except EOFError:
        print("[abort] stdin fechado", flush=True)
        return False
    return line == expected


async def _counts(db: AsyncSession) -> tuple[int, int]:
    nu = await db.scalar(select(func.count()).select_from(User))
    nw = await db.scalar(select(func.count()).select_from(Workspace))
    return int(nu or 0), int(nw or 0)


async def _delete_all_users(db: AsyncSession) -> None:
    if _is_sqlite(settings.DATABASE_URL):
        await db.execute(text("PRAGMA foreign_keys=ON"))
    await db.execute(delete(User))
    await db.commit()


def _wipe_storage(apply: bool) -> tuple[int, int]:
    """Remove todos os filhos de STORAGE_ROOT. Retorna (n_dir, bytes)."""
    root = _storage_root()
    if not root.exists():
        return 0, 0
    children = [p for p in root.iterdir()]
    total_bytes = sum(_du(p) for p in children)
    n = len(children)
    if apply:
        for p in children:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink(missing_ok=True)
    return n, total_bytes


def _flush_redis(apply: bool) -> tuple[bool, str]:
    if not apply:
        return True, "[dry-run] redis não tocado"
    try:
        import redis
    except ImportError:
        return False, "pacote redis não instalado — ignorado"
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.ping()
        r.flushdb()
        return True, f"FLUSHDB ok ({settings.REDIS_URL})"
    except Exception as e:
        return False, f"falhou ({e!r}) — continuar sem Redis"


async def run(*, apply: bool, skip_redis: bool) -> int:
    db_url = _redact_database_url(settings.DATABASE_URL)
    print("[config]", flush=True)
    print(f"  DATABASE_URL: {db_url}", flush=True)
    print(f"  STORAGE_ROOT: {_storage_root()}", flush=True)
    if not skip_redis:
        print(f"  REDIS_URL:    {settings.REDIS_URL}", flush=True)
    else:
        print("  REDIS:        (skip-redis)", flush=True)

    async with AsyncSessionLocal() as db:
        n_users, n_ws = await _counts(db)

    print("\n[estado actual]", flush=True)
    print(f"  users:      {n_users}", flush=True)
    print(f"  workspaces: {n_ws}", flush=True)

    n_st_items, st_bytes = _wipe_storage(apply=False)
    print(f"  storage:    {n_st_items} entradas, ~{_human(st_bytes)}", flush=True)

    if not apply:
        print(
            "\n[dry-run] Nada foi alterado. Use --apply para executar (com confirmações).",
            flush=True,
        )
        return 0

    print("\n*** ATENÇÃO: vai apagar TODOS os utilizadores e ficheiros de storage. ***", flush=True)

    if not _prompt_exact(
        "Confirmação 1 de 2 — reconhece que todos os dados de utilizador serão eliminados.",
        CONFIRM_PHRASE_1,
    ):
        print("[abort] primeira confirmação falhou", flush=True)
        return 2

    if not _prompt_exact(
        "Confirmação 2 de 2 — confirma que esta operação é permanente e irreversível.",
        CONFIRM_PHRASE_2,
    ):
        print("[abort] segunda confirmação falhou", flush=True)
        return 2

    async with AsyncSessionLocal() as db:
        await _delete_all_users(db)
    print("[done] DELETE FROM users (cascata aplicada)", flush=True)

    n_removed, freed = _wipe_storage(apply=True)
    print(f"[done] storage: removidas {n_removed} entradas (~{_human(freed)})", flush=True)

    if not skip_redis:
        ok, msg = _flush_redis(apply=True)
        print(("[done] " if ok else "[warn] ") + msg, flush=True)
        if not ok:
            print(
                "[warn] Redis não limpo — filas podem referenciar IDs antigos; "
                "reinicie workers ou corrija Redis manualmente.",
                flush=True,
            )

    async with AsyncSessionLocal() as db:
        nu, nw = await _counts(db)
    print("\n[estado final] users=", nu, "workspaces=", nw, flush=True)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar URL, contagens e tamanho de storage; não alterar nada",
    )
    g.add_argument(
        "--apply",
        action="store_true",
        help="Executar reset após duas confirmações interactivas",
    )
    ap.add_argument(
        "--skip-redis",
        action="store_true",
        help="Não executar FLUSHDB no Redis",
    )
    args = ap.parse_args()
    if args.dry_run and args.skip_redis:
        ap.error("--skip-redis só faz sentido com --apply")

    sys.exit(asyncio.run(run(apply=args.apply, skip_redis=args.skip_redis)))


if __name__ == "__main__":
    main()
