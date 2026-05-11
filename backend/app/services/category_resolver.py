"""Category resolver — merge ``category_templates`` + ``workspace_category_overrides`` (A7.3 · ADR-137).

Storage explícito de template global versionado vs override por workspace.
Read-path produz a lista mergeada que pipeline e UI consomem. Cache Redis com
invalidação por evento (``invalidate_resolved_categories(workspace_id)``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.category_template import (
    CategoryTemplate,
    WorkspaceCategoryOverride,
)
from backend.app.services import category_cache

#: Categorization metadata key — auxiliary blocks (pj_source_mapping,
#: internal_transfer_patterns, …) viajam pelo CategoryTemplate row com este
#: ``key`` reservado, dentro de ``metadata_json``. Evita criar tabela paralela
#: para o conteúdo non-category-tree de ``categorization.json``.
METADATA_TEMPLATE_KEY = "__categorization_metadata__"

ACTIVE_TEMPLATE_VERSION = 1


def get_active_template_version() -> int:
    """Versão do template ativa no resolver (ADR-185 §4; futura feature-flag por workspace)."""
    return ACTIVE_TEMPLATE_VERSION


def get_latest_template_version(db: Session) -> int:
    """``MAX(category_templates.template_version)`` cacheado em Redis (TTL 1h, invalidado por seed Alembic — ADR-185 §4)."""
    cached = category_cache.get_latest_template_version()
    if cached is not None:
        return cached
    latest = db.execute(select(func.max(CategoryTemplate.template_version))).scalar()
    resolved = ACTIVE_TEMPLATE_VERSION if latest is None else int(latest)
    category_cache.set_latest_template_version(resolved)
    return resolved


@dataclass(frozen=True)
class ResolvedCategory:
    """Categoria após merge template + override (A7.3)."""

    key: str
    label: str
    category_type: str
    keywords: tuple[str, ...]
    monthly_cap_brl_cents: Optional[int]
    sort_order: int
    parent_key: Optional[str]
    disabled: bool


def resolve_categories(
    workspace_id: str,
    db: Session,
    *,
    template_version: int = ACTIVE_TEMPLATE_VERSION,
) -> list[ResolvedCategory]:
    """Merge template + overrides; categorias ``disabled`` são filtradas.

    Cache Redis em ``category_cache``; invalidação ativa via
    ``category_cache.invalidate_resolved_categories``. Falha aberta — sem Redis,
    cai no DB sem stack-overhead extra.
    """
    cached = category_cache.get_cached_resolved(workspace_id, template_version)
    if cached is not None:
        return [_payload_to_resolved(p) for p in cached]
    template = _load_active_template(db, template_version)
    overrides = _load_overrides(db, workspace_id)
    resolved = _merge_template_and_overrides(template, overrides)
    category_cache.store_resolved_cache(
        workspace_id,
        template_version,
        [_resolved_to_payload(c) for c in resolved],
    )
    return resolved


def get_categorization_metadata(
    db: Session, *, template_version: int = ACTIVE_TEMPLATE_VERSION
) -> dict:
    """Retorna o blob auxiliar (``pj_source_mapping``, ``internal_transfer_patterns``…) do template."""
    row = db.execute(
        select(CategoryTemplate).where(
            CategoryTemplate.template_version == template_version,
            CategoryTemplate.key == METADATA_TEMPLATE_KEY,
        )
    ).scalar_one_or_none()
    if row is None:
        return {}
    return dict(row.metadata_json or {})


def _load_active_template(db: Session, template_version: int) -> list[CategoryTemplate]:
    rows = (
        db.execute(
            select(CategoryTemplate)
            .where(CategoryTemplate.template_version == template_version)
            .where(CategoryTemplate.key != METADATA_TEMPLATE_KEY)
            .order_by(CategoryTemplate.sort_order, CategoryTemplate.key)
        )
        .scalars()
        .all()
    )
    return list(rows)


def _load_overrides(db: Session, workspace_id: str) -> dict[str, WorkspaceCategoryOverride]:
    rows = (
        db.execute(
            select(WorkspaceCategoryOverride).where(
                WorkspaceCategoryOverride.workspace_id == workspace_id
            )
        )
        .scalars()
        .all()
    )
    return {row.template_key: row for row in rows}


def _merge_template_and_overrides(
    template: list[CategoryTemplate],
    overrides_by_key: dict[str, WorkspaceCategoryOverride],
) -> list[ResolvedCategory]:
    resolved: list[ResolvedCategory] = []
    for tmpl in template:
        ov = overrides_by_key.get(tmpl.key)
        if ov is not None and ov.disabled:
            continue
        resolved.append(_merge_one(tmpl, ov))
    return resolved


def _merge_one(tmpl: CategoryTemplate, ov: Optional[WorkspaceCategoryOverride]) -> ResolvedCategory:
    if ov is None:
        return _resolved_from_template(tmpl)
    label = ov.label_override if ov.label_override is not None else tmpl.label
    keywords = (
        tuple(ov.keywords_override)
        if ov.keywords_override is not None
        else tuple(tmpl.default_keywords)
    )
    cap = (
        ov.monthly_cap_brl_cents_override
        if ov.monthly_cap_brl_cents_override is not None
        else tmpl.default_monthly_cap_brl_cents
    )
    return ResolvedCategory(
        key=tmpl.key,
        label=label,
        category_type=tmpl.category_type,
        keywords=keywords,
        monthly_cap_brl_cents=cap,
        sort_order=tmpl.sort_order,
        parent_key=tmpl.parent_key,
        disabled=False,
    )


def _resolved_from_template(tmpl: CategoryTemplate) -> ResolvedCategory:
    return ResolvedCategory(
        key=tmpl.key,
        label=tmpl.label,
        category_type=tmpl.category_type,
        keywords=tuple(tmpl.default_keywords or ()),
        monthly_cap_brl_cents=tmpl.default_monthly_cap_brl_cents,
        sort_order=tmpl.sort_order,
        parent_key=tmpl.parent_key,
        disabled=False,
    )


def _resolved_to_payload(c: ResolvedCategory) -> dict:
    return {
        "key": c.key,
        "label": c.label,
        "category_type": c.category_type,
        "keywords": list(c.keywords),
        "monthly_cap_brl_cents": c.monthly_cap_brl_cents,
        "sort_order": c.sort_order,
        "parent_key": c.parent_key,
        "disabled": c.disabled,
    }


def _payload_to_resolved(p: dict) -> ResolvedCategory:
    return ResolvedCategory(
        key=p["key"],
        label=p["label"],
        category_type=p["category_type"],
        keywords=tuple(p["keywords"]),
        monthly_cap_brl_cents=p.get("monthly_cap_brl_cents"),
        sort_order=p["sort_order"],
        parent_key=p.get("parent_key"),
        disabled=p.get("disabled", False),
    )
