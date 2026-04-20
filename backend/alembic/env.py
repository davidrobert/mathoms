"""Alembic env.py — async-aware migration runner for SQLAlchemy 2.0.

# F6.5E.4 — cwd guard

Bug histórico (durante fix de BUG-015): `alembic upgrade head` foi rodado da
raiz e aplicou migration na DB errada porque `sqlalchemy.url` em alembic.ini
era relativa (`sqlite:///./mathoms.db`) e o `cwd` do momento determinava qual
arquivo `mathoms.db` recebia o schema novo.

**Política aplicada (F6.5E.4):**
- Se `MATHOMS_DATABASE_URL` estiver setada via env, ela vence (Pydantic Settings
  já injeta em `settings.DATABASE_URL`).
- Caso contrário, a URL vem do `alembic.ini` que agora usa `%(here)s/../mathoms.db`
  (caminho absoluto resolvido a partir do diretório do .ini).
- O guard abaixo **rejeita explicitamente** SQLite com path relativo
  (`sqlite:///./...` ou `sqlite:///mathoms.db` sem prefixo absoluto), forçando
  o operador a corrigir antes de rodar.

Para sair do guard em CI/prod: defina `MATHOMS_DATABASE_URL` apontando para o
banco real (PostgreSQL recomendado).

Bypass para uso programático em testes: `MATHOMS_ALEMBIC_ALLOW_RELATIVE_SQLITE=1`
(NÃO use em produção — somente em tests que provam o próprio guard).
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from backend.app.core.config import settings
from backend.app.core.database import Base

# Import all models so Base.metadata knows about them
import backend.app.models  # noqa: F401


def _resolve_db_url() -> str:
    """Decide qual URL usar e rejeita SQLite com path relativo ambíguo."""
    url = settings.DATABASE_URL

    # Guard: SQLite sem path absoluto = recusar (a menos que bypass explícito).
    if url.startswith(("sqlite:///", "sqlite+aiosqlite:///", "sqlite+pysqlite:///")):
        path_part = url.split(":///", 1)[1]
        is_absolute = path_part.startswith("/") or (
            len(path_part) >= 3 and path_part[1:3] == ":\\"  # Windows
        )
        if not is_absolute and not os.environ.get("MATHOMS_ALEMBIC_ALLOW_RELATIVE_SQLITE"):
            resolved = Path(os.getcwd()) / path_part
            sys.stderr.write(
                "\n"
                "✗ ALEMBIC GUARD (F6.5E.4): SQLite URL relativo detectado.\n"
                f"  URL configurada: {url!r}\n"
                f"  Resolveria para: {resolved}\n"
                f"  cwd atual:       {os.getcwd()}\n"
                "\n"
                "Migrations relativas podem aplicar na DB errada por acidente.\n"
                "Conserte de uma das formas:\n"
                "  • Setar MATHOMS_DATABASE_URL com path absoluto:\n"
                "      export MATHOMS_DATABASE_URL='sqlite+aiosqlite:////caminho/abs/mathoms.db'\n"
                "  • Ou rodar a partir da raiz do repo (alembic.ini agora usa %(here)s).\n"
                "  • Bypass apenas para testes do próprio guard:\n"
                "      MATHOMS_ALEMBIC_ALLOW_RELATIVE_SQLITE=1\n\n"
            )
            raise SystemExit(2)

    return url


config = context.config
config.set_main_option("sqlalchemy.url", _resolve_db_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Dispatch to async runner."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
