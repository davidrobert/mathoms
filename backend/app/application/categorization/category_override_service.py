"""``CategoryOverrideService`` — orquestra repo + cache invalidation (A11.W1 · ADR-185)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.repositories.workspace_category_override_repository import (
    WorkspaceCategoryOverrideRepository,
)
from backend.app.services import category_cache

logger = get_logger("categorization.override")


@dataclass(frozen=True)
class CategoryOverrideConfig:
    """Diff a aplicar sobre o template global do workspace (ADR-097 D3 frozen value object)."""

    workspace_id: str
    template_key: str
    label_override: Optional[str] = None
    keywords_override: Optional[list[str]] = None
    monthly_cap_brl_cents_override: Optional[int] = None
    disabled: bool = False
    updated_by_user_id: Optional[str] = None


class CategoryOverrideService:
    """Service async — owns commit + cache invalidation por write."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WorkspaceCategoryOverrideRepository(session)

    async def upsert(self, config: CategoryOverrideConfig) -> str:
        """Cria ou atualiza override; retorna ``override.id``."""
        override = await self._repo.upsert(
            config.workspace_id,
            config.template_key,
            label_override=config.label_override,
            keywords_override=config.keywords_override,
            monthly_cap_brl_cents_override=config.monthly_cap_brl_cents_override,
            disabled=config.disabled,
        )
        await self._session.commit()
        await self._session.refresh(override)
        _invalidate_cache(config, action="upsert")
        return override.id

    async def disable(self, workspace_id: str, template_key: str) -> None:
        """Oculta categoria via override.disabled=True (mantém row para auditoria)."""
        config = CategoryOverrideConfig(
            workspace_id=workspace_id, template_key=template_key, disabled=True
        )
        await self._repo.upsert(workspace_id, template_key, disabled=True)
        await self._session.commit()
        _invalidate_cache(config, action="disable")

    async def reset(self, workspace_id: str, template_key: str) -> None:
        """Apaga override → categoria volta ao default do template."""
        existing = await self._repo.get_by_template_key(workspace_id, template_key)
        if existing is None:
            return
        await self._repo.delete(existing)
        await self._session.commit()
        _invalidate_cache(
            CategoryOverrideConfig(workspace_id=workspace_id, template_key=template_key),
            action="reset",
        )


def _invalidate_cache(config: CategoryOverrideConfig, *, action: str) -> None:
    """Write-through pós-commit; falha de invalidação loga warning, não aborta o write."""
    try:
        category_cache.invalidate_resolved_categories(config.workspace_id)
    except Exception as exc:  # pragma: no cover — defensive; falha aberta
        logger.warning(
            "category override cache invalidation failed",
            extra=_log_extra(config, action=action, error=str(exc)),
        )
        return
    logger.info("category override applied", extra=_log_extra(config, action=action))


def _log_extra(config: CategoryOverrideConfig, *, action: str, error: str | None = None) -> dict:
    extra = {
        "workspace_id": config.workspace_id,
        "template_key": config.template_key,
        "action": action,
        "disabled": config.disabled,
        "updated_by_user_id": config.updated_by_user_id,
    }
    if error is not None:
        extra["error"] = error
    return extra
