"""Repository: ``InstitutionCatalog`` (global). Sync — usado em worker e seeds."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.institution_catalog import InstitutionCatalog


class InstitutionCatalogRepository:
    """Single Responsibility: leitura sync do catálogo global."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[InstitutionCatalog]:
        rows = (
            self._session.execute(select(InstitutionCatalog).order_by(InstitutionCatalog.code))
            .scalars()
            .all()
        )
        return list(rows)

    def get_by_code(self, code: str) -> Optional[InstitutionCatalog]:
        return self._session.execute(
            select(InstitutionCatalog).where(InstitutionCatalog.code == code)
        ).scalar_one_or_none()
