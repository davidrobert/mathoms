"""RefreshTokenFamily — refresh token rotativo com family revocation (ADR-170 · W3-T03)."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RefreshTokenFamily(Base):
    """Uma linha por login (família); persiste apenas hashes sha256 do secret.
    Reuse fora da grace window revoga a família inteira; ``expires_at`` desliza
    +7d por rotação com teto absoluto de 30d (ADR-170, emenda W3-T03)."""

    __tablename__ = "refresh_token_families"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Snapshot de User.token_version no login — tv bump (forced logout F9)
    # revoga a família na próxima rotação, não só os access tokens.
    token_version_at_issue: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Grace window anti-falso-positivo: 2 tabs refrescando em <60s não é reuse.
    prev_token_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    prev_rotated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rotation_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
