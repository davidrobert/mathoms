"""Use cases A7.3 (ADR-137): list/upsert/delete sobre overrides + template.

Frontend mantém contrato estável (``CategoryListResponse``); backend grava em
``workspace_category_overrides`` em vez de ``categories``. ``code`` no DTO
mapeia para ``template_key``; ``id`` no DTO é o id do override (quando existe).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.repositories.workspace_category_override_repository import (
    WorkspaceCategoryOverrideRepository,
)
from backend.app.schemas.dto.category import (
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdateCommand,
)
from backend.app.services import category_cache
from backend.app.services.category_resolver import (
    METADATA_TEMPLATE_KEY,
    ResolvedCategory,
    resolve_categories,
)


async def list_categories_resolved(workspace_id: str, *, db: AsyncSession) -> CategoryListResponse:
    """``GET /categories`` — retorna template + overrides mergeados."""
    resolved = await db.run_sync(
        lambda sync_session: resolve_categories(workspace_id, sync_session)
    )
    overrides = await WorkspaceCategoryOverrideRepository(db).list_by_workspace(workspace_id)
    override_id_by_key = {ov.template_key: ov.id for ov in overrides}
    items = [
        _resolved_to_response(c, override_id_by_key.get(c.key))
        for c in resolved
        if c.key != METADATA_TEMPLATE_KEY
    ]
    return CategoryListResponse(categories=items, total=len(items))


async def upsert_category_override(
    template_key: str,
    cmd: CategoryUpdateCommand,
    *,
    workspace_id: str,
    db: AsyncSession,
) -> CategoryResponse:
    """``PUT /categories/{key}`` — escreve em ``workspace_category_overrides``."""
    resolved = await db.run_sync(
        lambda sync_session: resolve_categories(workspace_id, sync_session)
    )
    by_key = {c.key: c for c in resolved}
    if template_key not in by_key:
        raise NotFoundError(
            f"Categoria '{template_key}' não está no template global",
            code="category_not_in_template",
        )
    overrides = await WorkspaceCategoryOverrideRepository(db).upsert(
        workspace_id,
        template_key,
        label_override=_diff_or_none(cmd.name, by_key[template_key].label),
        keywords_override=_keywords_diff(cmd.keywords, by_key[template_key].keywords),
        monthly_cap_brl_cents_override=_cap_diff(
            cmd.monthly_cap, by_key[template_key].monthly_cap_brl_cents
        ),
        disabled=False,
    )
    category_cache.invalidate_resolved_categories(workspace_id)
    refreshed = await db.run_sync(
        lambda sync_session: resolve_categories(workspace_id, sync_session)
    )
    new_by_key = {c.key: c for c in refreshed}
    return _resolved_to_response(new_by_key[template_key], overrides.id)


async def disable_category_override(
    template_key: str,
    *,
    workspace_id: str,
    db: AsyncSession,
) -> None:
    """``DELETE /categories/{key}`` — desabilita categoria via override.disabled=True."""
    repo = WorkspaceCategoryOverrideRepository(db)
    await repo.upsert(
        workspace_id,
        template_key,
        disabled=True,
    )
    category_cache.invalidate_resolved_categories(workspace_id)


async def reset_category_override(
    template_key: str,
    *,
    workspace_id: str,
    db: AsyncSession,
) -> None:
    """``DELETE /categories/{key}/override`` — apaga override; volta ao template default."""
    repo = WorkspaceCategoryOverrideRepository(db)
    existing = await repo.get_by_template_key(workspace_id, template_key)
    if existing is None:
        return
    await repo.delete(existing)
    category_cache.invalidate_resolved_categories(workspace_id)


def _diff_or_none(value: str | None, default: str) -> str | None:
    if value is None or value == default:
        return None
    return value


def _keywords_diff(value: list[str] | None, default: tuple[str, ...]) -> list[str] | None:
    if value is None:
        return None
    if list(value) == list(default):
        return None
    return list(value)


def _cap_diff(value: float | None, default: int | None) -> int | None:
    if value is None:
        return None
    cents = int(round(value * 100))
    if cents == default:
        return None
    return cents


def _resolved_to_response(resolved: ResolvedCategory, override_id: str | None) -> CategoryResponse:
    monthly_cap = (
        float(resolved.monthly_cap_brl_cents) / 100.0
        if resolved.monthly_cap_brl_cents is not None
        else None
    )
    return CategoryResponse(
        id=override_id,
        code=resolved.key,
        name=resolved.label,
        category_type=resolved.category_type,
        monthly_cap=monthly_cap,
        order=resolved.sort_order,
        keywords=list(resolved.keywords),
    )
