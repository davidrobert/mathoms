"""Repository: ``CategoryTemplate`` (global, versioned). Sync — usado em worker.

Workspace nunca muta template; mutation é seed Alembic. Repository expõe leitura
e helpers de seed para data migrations.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.category_template import CategoryTemplate


class CategoryTemplateRepository:
    """Single Responsibility: leitura de ``category_templates`` (sync)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active(self, *, template_version: int) -> list[CategoryTemplate]:
        """Retorna templates da versão ordenados por ``sort_order, key`` (exclui metadata row)."""
        from backend.app.services.category_resolver import METADATA_TEMPLATE_KEY

        rows = self._session.execute(
            select(CategoryTemplate)
            .where(CategoryTemplate.template_version == template_version)
            .where(CategoryTemplate.key != METADATA_TEMPLATE_KEY)
            .order_by(CategoryTemplate.sort_order, CategoryTemplate.key)
        ).scalars().all()
        return list(rows)

    def get_by_key(
        self, *, template_version: int, key: str
    ) -> Optional[CategoryTemplate]:
        return self._session.execute(
            select(CategoryTemplate).where(
                CategoryTemplate.template_version == template_version,
                CategoryTemplate.key == key,
            )
        ).scalar_one_or_none()
