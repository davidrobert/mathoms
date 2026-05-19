"""``AssetCatalog`` (global versionado) + ``WorkspaceAssetOverride`` (diff per-workspace) — lastro_moeda por ativo (ADR-224 · A12; pattern espelha ``institution_catalog`` + ADR-215; priority override > ticker > cnpj > keyword > fallback)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class AssetCatalog(Base):
    """Catálogo global de ativos com lastro_moeda canônico."""

    __tablename__ = "asset_catalog"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    catalog_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(12), nullable=True, index=True)
    cnpj: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    match_keyword: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    asset_class: Mapped[str] = mapped_column(String(40), nullable=False)
    lastro_moeda: Mapped[str] = mapped_column(String(8), nullable=False)
    lastro_source: Mapped[str] = mapped_column(String(20), nullable=False, default="catalog")
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class WorkspaceAssetOverride(Base):
    """Override per-workspace de lastro_moeda — diff vs ``asset_catalog`` global."""

    __tablename__ = "workspace_asset_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_match_key: Mapped[str] = mapped_column(String(200), nullable=False)
    match_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    lastro_moeda: Mapped[str] = mapped_column(String(8), nullable=False)
    override_source: Mapped[str] = mapped_column(String(20), nullable=False, default="user_manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
