"""Institution catalog resolver — global catalog único (A7.3 · ADR-137).

Cliente não customiza catálogo nesta lane (banco fora da lista é ticket de
produto). Apenas leitura cacheada da tabela ``institution_catalog``. Falha
aberta — sem Redis, cai no DB.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.institution_catalog import InstitutionCatalog
from pipeline.domain.types.config import InstitutionDef, InstitutionsCatalog

logger = logging.getLogger(__name__)

_CATALOG_CACHE_KEY = "institution_catalog:global"
_CATALOG_TTL_SECONDS = 86400 * 30


def resolve_institutions(db: Session) -> InstitutionsCatalog:
    """Lê catálogo global (cached). Cliente sem custom row → catálogo vazio."""
    cached = _get_cached_catalog()
    if cached is not None:
        return _payload_to_catalog(cached)
    rows = db.execute(select(InstitutionCatalog).order_by(InstitutionCatalog.code)).scalars().all()
    catalog = _rows_to_catalog(list(rows))
    _store_catalog_cache([_def_to_payload(d) for d in catalog.institutions.values()])
    return catalog


def invalidate_catalog() -> None:
    """Invalida cache — chamar em mutations admin do catálogo."""
    _redis_delete(_CATALOG_CACHE_KEY)


def _rows_to_catalog(rows: list[InstitutionCatalog]) -> InstitutionsCatalog:
    institutions = {
        row.code: InstitutionDef(
            code=row.code,
            name=row.name,
            parser=row.default_parser,
            metadata={"category": row.category, **(row.metadata_json or {})},
        )
        for row in rows
    }
    return InstitutionsCatalog(institutions=institutions)


def _def_to_payload(d: InstitutionDef) -> dict:
    return {
        "code": d.code,
        "name": d.name,
        "parser": d.parser,
        "metadata": dict(d.metadata),
    }


def _payload_to_catalog(payload: list[dict]) -> InstitutionsCatalog:
    institutions = {
        item["code"]: InstitutionDef(
            code=item["code"],
            name=item["name"],
            parser=item.get("parser"),
            metadata=item.get("metadata") or {},
        )
        for item in payload
    }
    return InstitutionsCatalog(institutions=institutions)


def _get_cached_catalog() -> list[dict] | None:
    raw = _redis_get(_CATALOG_CACHE_KEY)
    if raw is None:
        return None
    try:
        return list(json.loads(raw))
    except (ValueError, TypeError) as exc:
        logger.warning("institution catalog cache parse failed: %s", exc)
        return None


def _store_catalog_cache(payload: list[dict]) -> None:
    _redis_set(_CATALOG_CACHE_KEY, json.dumps(payload), _CATALOG_TTL_SECONDS)


def _redis_get(key: str) -> str | None:
    client = _get_redis_safe()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception as exc:
        logger.warning("redis GET failed for %s: %s", key, exc)
        return None


def _redis_set(key: str, value: str, ttl_seconds: int) -> None:
    client = _get_redis_safe()
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl_seconds)
    except Exception as exc:
        logger.warning("redis SET failed for %s: %s", key, exc)


def _redis_delete(key: str) -> None:
    client = _get_redis_safe()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as exc:
        logger.warning("redis DEL failed for %s: %s", key, exc)


def _get_redis_safe() -> Any:
    try:
        from backend.app.services.events import _get_redis

        return _get_redis()
    except Exception:
        return None
