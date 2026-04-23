"""Regressão: pragmas SQLite no engine sync e async.

Sem WAL + busy_timeout, Celery + FastAPI + pipeline produzem
``database is locked`` sob carga (incidente 2026-04-23).
"""

from __future__ import annotations

import asyncio

import pytest

from backend.app.core.database import engine, sync_engine


def _is_sqlite(url: str) -> bool:
    return str(url).startswith("sqlite")


@pytest.mark.skipif(
    not _is_sqlite(sync_engine.url.render_as_string(hide_password=False)),
    reason="pragmas aplicam só quando backend é SQLite",
)
def test_sync_engine_sqlite_pragmas():
    with sync_engine.connect() as conn:
        journal_mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
        busy_timeout = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
        synchronous = conn.exec_driver_sql("PRAGMA synchronous").scalar()

    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) >= 30_000
    assert int(synchronous) == 1  # NORMAL


@pytest.mark.skipif(
    not _is_sqlite(engine.url.render_as_string(hide_password=False)),
    reason="pragmas aplicam só quando backend é SQLite",
)
def test_async_engine_sqlite_pragmas():
    async def _check():
        async with engine.connect() as conn:
            journal_mode = (await conn.exec_driver_sql("PRAGMA journal_mode")).scalar()
            busy_timeout = (await conn.exec_driver_sql("PRAGMA busy_timeout")).scalar()
        return journal_mode, busy_timeout

    journal_mode, busy_timeout = asyncio.run(_check())
    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) >= 30_000
