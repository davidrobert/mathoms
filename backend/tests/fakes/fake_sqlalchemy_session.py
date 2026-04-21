"""Minimal in-memory SQLAlchemy-shaped session for pure-function tests.

Only implements `scalars(stmt).all()`, which is the surface exercised by
stateless helpers like `build_premissas_snapshot_sync`. Anything that
needs real persistence (`add`, `flush`, joins) should use the real
SQLite-backed fixtures in `backend/tests/conftest.py`.
"""

from __future__ import annotations

from typing import Any, Iterable


class _ScalarResult:
    def __init__(self, rows: Iterable[Any]) -> None:
        self._rows = list(rows)

    def all(self) -> list[Any]:
        return list(self._rows)


class FakeScalarSession:
    """Stub Session that returns a preset list for any `scalars(...)` call."""

    def __init__(self, rows: Iterable[Any] = ()) -> None:
        self._rows = list(rows)

    def scalars(self, _stmt: Any) -> _ScalarResult:
        return _ScalarResult(self._rows)
