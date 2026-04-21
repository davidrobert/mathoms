"""Fake sync-style SQLAlchemy session + factory for legacy tests.

These mirror `SyncSessionLocal()` usage inside `pipeline_service`
(`with SyncSessionLocal() as db: db.query(...).filter(...).first()`
and `db.get(Model, id)`), so we can rewire those helpers without
standing up a real SQLite engine.

Prefer the real `db` fixture + factories whenever the test touches
persistence semantics; this fake only exists to replace ad-hoc
`MagicMock` scaffolding.
"""

from __future__ import annotations

from typing import Any


class _Query:
    def __init__(self, first_result: Any) -> None:
        self._first = first_result

    def filter(self, *_args: Any, **_kwargs: Any) -> "_Query":
        return self

    def first(self) -> Any:
        return self._first


class FakeSyncDbSession:
    """Minimal sync session with `.query(...)` chain and `.get(model, id)`."""

    def __init__(
        self,
        *,
        get_result: Any = None,
        query_first: Any = None,
    ) -> None:
        self.get_result = get_result
        self.query_first = query_first
        self.committed = False

    def query(self, _model: Any) -> _Query:
        return _Query(self.query_first)

    def get(self, _model: Any, _pk: Any) -> Any:
        return self.get_result

    def commit(self) -> None:
        self.committed = True

    def refresh(self, _obj: Any) -> None:
        return None


class FakeSyncSessionFactory:
    """Callable context manager matching `SyncSessionLocal()` usage."""

    def __init__(self, session: FakeSyncDbSession) -> None:
        self._session = session

    def __call__(self) -> "FakeSyncSessionFactory":
        return self

    def __enter__(self) -> FakeSyncDbSession:
        return self._session

    def __exit__(self, *_exc: Any) -> bool:
        return False
