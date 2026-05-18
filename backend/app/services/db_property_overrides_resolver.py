"""`DBPropertyOverridesResolver` — adapter SQLAlchemy sync do `PropertyOverridesResolver` (ADR-215 P3)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import WorkspacePropertyOverride


class DBPropertyOverridesResolver:
    """Lê `workspace_property_overrides` (sync) para o pipeline E5."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_workspace(self, workspace_id: str) -> dict[str, str]:
        stmt = select(WorkspacePropertyOverride).where(
            WorkspacePropertyOverride.workspace_id == workspace_id
        )
        rows = self._session.execute(stmt).scalars().all()
        return {row.property_id: row.classification for row in rows}
