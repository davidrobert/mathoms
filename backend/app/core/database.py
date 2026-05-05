"""Database engine and session factory — async (endpoints) + sync (background threads)."""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.core.config import settings

# SQLite concurrency: WAL permite leitores concorrentes com o writer, e
# busy_timeout faz o driver esperar (em vez de levantar OperationalError)
# quando outro processo segura o lock. Sem isso, Celery + FastAPI + pipeline
# escrevendo no mesmo arquivo produzem "database is locked" sob carga.
_SQLITE_BUSY_TIMEOUT_MS = 30_000
_SQLITE_CONNECT_TIMEOUT_S = 30


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _sqlite_connect_args(url: str) -> dict:
    if not _is_sqlite(url):
        return {}
    return {"timeout": _SQLITE_CONNECT_TIMEOUT_S, "check_same_thread": False}


def _apply_sqlite_pragmas(dbapi_conn, _connection_record) -> None:
    cur = dbapi_conn.cursor()
    try:
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
        # foreign_keys intencionalmente fora do escopo deste fix — ligar
        # expõe FK violations históricas em fixtures de teste. Tema separado.
    finally:
        cur.close()


def attach_sqlite_pragmas(target_engine) -> None:
    """Anexa listener de PRAGMA no engine (idempotente). Usado também por
    conftest de testes — engines de teste criados fora deste módulo precisam
    dos mesmos pragmas para evitar ``database is locked`` em paralelismo."""
    sync_target = getattr(target_engine, "sync_engine", target_engine)
    url = str(sync_target.url)
    if not _is_sqlite(url):
        return
    event.listen(sync_target, "connect", _apply_sqlite_pragmas)


# --- Async engine (used by FastAPI endpoints) ---

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    connect_args=_sqlite_connect_args(settings.DATABASE_URL),
)

attach_sqlite_pragmas(engine)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# --- Sync engine (used by background threads running the pipeline) ---

sync_engine = create_engine(
    settings.sync_database_url,
    echo=settings.DEBUG,
    future=True,
    connect_args=_sqlite_connect_args(settings.sync_database_url),
)

attach_sqlite_pragmas(sync_engine)

SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency that yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Bootstrap de DB efêmero (smoke test / fixture). Não usar no lifespan da API."""
    # create_all() bypassa alembic_version — usar fora de smoke/teste causa
    # schema drift que faz `alembic upgrade head` quebrar em migration posterior.
    # Caminho canônico de schema é `make migrate`.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
