"""Database engine and session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


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
    """Create all tables (dev only — production uses Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
