"""``CategoryTemplate`` + ``WorkspaceCategoryOverride`` (ADR-137 · A7.3).

Split do agregado ``Category`` em (a) **template global** versionado mantido
por seed Alembic (taxonomia base de produto) e (b) **overrides por workspace**
contendo apenas o diff vs template. Resolver no read-path produz a lista
mergeada que o pipeline e a UI consomem.

Money em ``BigInteger`` cents (ADR-090). Keywords em ``JSON`` array — SQLite
não suporta ``ARRAY`` nativo; mantemos compat dev.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class CategoryTemplate(Base):
    """Taxonomia base global (versionada). Seedada em Alembic; nunca rename de ``key``."""

    __tablename__ = "category_templates"
    __table_args__ = (
        UniqueConstraint(
            "template_version", "key", name="uq_category_templates_version_key"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    template_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, index=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    parent_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    category_type: Mapped[str] = mapped_column(String(10), nullable=False)
    default_keywords: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    default_monthly_cap_brl_cents: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class WorkspaceCategoryOverride(Base):
    """Override por workspace — somente diff vs template (label/keywords/cap/disabled)."""

    __tablename__ = "workspace_category_overrides"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "template_key", name="uq_ws_cat_override_ws_key"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    label_override: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    keywords_override: Mapped[Optional[list[str]]] = mapped_column(
        JSON, nullable=True
    )
    monthly_cap_brl_cents_override: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
