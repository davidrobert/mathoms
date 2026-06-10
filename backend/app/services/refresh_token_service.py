"""Refresh token rotativo com family revocation (ADR-170 · W3-T03) — wire
``<family_id>.<secret>``, persiste só sha256; secret independente de
SECRET_KEY/Fernet (rotação de chaves do app não invalida sessões)."""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.refresh_token_family import RefreshTokenFamily

logger = logging.getLogger("mathoms.auth.refresh")

REFRESH_COOKIE_NAME = "fin_refresh"


@dataclass(frozen=True)
class RefreshRotation:
    user_id: str
    family_id: str
    # None em grace hit: o cookie jar do browser (compartilhado entre tabs)
    # já contém o secret vigente — não rotacionar de novo nem sobrescrever.
    cookie_value: Optional[str]
    expires_at: datetime
    token_version_at_issue: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    # SQLite devolve naive mesmo com DateTime(timezone=True).
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _sliding_expiry(created_at: datetime) -> datetime:
    cap = _aware(created_at) + timedelta(days=settings.AUTH_REFRESH_ABSOLUTE_CAP_DAYS)
    return min(_utcnow() + timedelta(days=settings.AUTH_REFRESH_TTL_DAYS), cap)


def parse_refresh_cookie(cookie_value: str) -> Optional[tuple[str, str]]:
    """Retorna ``(family_id, secret)`` ou None se o formato não casa."""
    family_id, sep, secret = cookie_value.partition(".")
    if not sep or not family_id or not secret:
        return None
    return family_id, secret


async def issue_refresh_family(
    db: AsyncSession, user_id: str, *, token_version: int = 0
) -> tuple[str, datetime]:
    """Cria família nova (1 por login), com purge oportunístico das famílias
    mortas do usuário; retorna ``(cookie_value, expires_at)``. Caller comita."""
    await _purge_stale_families(db, user_id)
    secret = secrets.token_urlsafe(32)
    now = _utcnow()
    family = RefreshTokenFamily(
        user_id=user_id,
        token_hash=_hash_secret(secret),
        token_version_at_issue=token_version,
        expires_at=now + timedelta(days=settings.AUTH_REFRESH_TTL_DAYS),
    )
    db.add(family)
    await db.flush()
    logger.info("refresh_family_issued", extra={"family_id": family.id})
    return f"{family.id}.{secret}", family.expires_at


async def rotate_refresh_token(db: AsyncSession, cookie_value: str) -> Optional[RefreshRotation]:
    """Rotaciona o secret da família; None = inválido/expirado/revogado/reuse.
    Caller comita (inclusive no reuse — o revoke precisa persistir)."""
    parsed = parse_refresh_cookie(cookie_value)
    if parsed is None:
        return None
    family_id, secret = parsed
    family = await db.get(RefreshTokenFamily, family_id)
    if family is None or not _family_alive(family):
        return None
    return _resolve_presented_hash(family, _hash_secret(secret))


def _resolve_presented_hash(
    family: RefreshTokenFamily, presented: str
) -> Optional[RefreshRotation]:
    if presented == family.token_hash:
        return _rotate(family)
    if _is_grace_hit(family, presented):
        logger.info("refresh_grace_hit", extra={"family_id": family.id})
        return RefreshRotation(
            family.user_id,
            family.id,
            None,
            _aware(family.expires_at),
            family.token_version_at_issue,
        )
    family.revoked_at = _utcnow()
    logger.warning("refresh_reuse_detected", extra={"family_id": family.id})
    return None


async def revoke_family(db: AsyncSession, family_id: str) -> None:
    """Revoga por id — usado quando `tv` divergiu (forced logout F9). Caller comita."""
    family = await db.get(RefreshTokenFamily, family_id)
    if family is not None and family.revoked_at is None:
        family.revoked_at = _utcnow()
        logger.info("refresh_family_revoked", extra={"family_id": family.id})


async def revoke_family_by_cookie(db: AsyncSession, cookie_value: str) -> bool:
    """Logout: revoga a família do cookie apresentado. Caller comita."""
    parsed = parse_refresh_cookie(cookie_value)
    if parsed is None:
        return False
    family = await db.get(RefreshTokenFamily, parsed[0])
    if family is None or family.revoked_at is not None:
        return False
    family.revoked_at = _utcnow()
    logger.info("refresh_family_revoked", extra={"family_id": family.id})
    return True


def _family_alive(family: RefreshTokenFamily) -> bool:
    return family.revoked_at is None and _aware(family.expires_at) > _utcnow()


def _is_grace_hit(family: RefreshTokenFamily, presented_hash: str) -> bool:
    if family.prev_token_hash is None or family.prev_rotated_at is None:
        return False
    window = timedelta(seconds=settings.AUTH_REFRESH_GRACE_WINDOW_S)
    return presented_hash == family.prev_token_hash and (
        _utcnow() - _aware(family.prev_rotated_at) < window
    )


def _rotate(family: RefreshTokenFamily) -> RefreshRotation:
    new_secret = secrets.token_urlsafe(32)
    now = _utcnow()
    family.prev_token_hash = family.token_hash
    family.prev_rotated_at = now
    family.token_hash = _hash_secret(new_secret)
    family.rotation_count += 1
    family.last_used_at = now
    family.expires_at = _sliding_expiry(family.created_at)
    logger.info(
        "refresh_rotated",
        extra={"family_id": family.id, "rotation_count": family.rotation_count},
    )
    return RefreshRotation(
        family.user_id,
        family.id,
        f"{family.id}.{new_secret}",
        _aware(family.expires_at),
        family.token_version_at_issue,
    )


async def _purge_stale_families(db: AsyncSession, user_id: str) -> None:
    await db.execute(
        delete(RefreshTokenFamily).where(
            RefreshTokenFamily.user_id == user_id,
            or_(
                RefreshTokenFamily.revoked_at.is_not(None),
                RefreshTokenFamily.expires_at < _utcnow(),
            ),
        )
    )
