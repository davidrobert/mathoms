"""Repositories: ``AssetCatalog`` (global) + ``WorkspaceAssetOverride`` (diff). ADR-224 PR-A."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.asset_catalog import AssetCatalog, WorkspaceAssetOverride


class AssetCatalogRepository:
    """Leitura sync do catálogo global versionado (catalog_version)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_version(self, catalog_version: int = 1) -> list[AssetCatalog]:
        rows = (
            self._session.execute(
                select(AssetCatalog)
                .where(AssetCatalog.catalog_version == catalog_version)
                .order_by(AssetCatalog.asset_class, AssetCatalog.ticker, AssetCatalog.match_keyword)
            )
            .scalars()
            .all()
        )
        return list(rows)

    def get_by_ticker(self, ticker: str, catalog_version: int = 1) -> Optional[AssetCatalog]:
        return self._session.execute(
            select(AssetCatalog).where(
                AssetCatalog.ticker == ticker,
                AssetCatalog.catalog_version == catalog_version,
            )
        ).scalar_one_or_none()

    def get_by_cnpj(self, cnpj: str, catalog_version: int = 1) -> Optional[AssetCatalog]:
        return self._session.execute(
            select(AssetCatalog).where(
                AssetCatalog.cnpj == cnpj,
                AssetCatalog.catalog_version == catalog_version,
            )
        ).scalar_one_or_none()


class WorkspaceAssetOverrideRepository:
    """Reads + writes para override per-workspace (sticky pattern ADR-215)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_workspace(self, workspace_id: str) -> list[WorkspaceAssetOverride]:
        rows = (
            self._session.execute(
                select(WorkspaceAssetOverride)
                .where(WorkspaceAssetOverride.workspace_id == workspace_id)
                .order_by(WorkspaceAssetOverride.asset_match_key)
            )
            .scalars()
            .all()
        )
        return list(rows)

    def get(
        self, workspace_id: str, match_kind: str, asset_match_key: str
    ) -> Optional[WorkspaceAssetOverride]:
        return self._session.execute(
            select(WorkspaceAssetOverride).where(
                WorkspaceAssetOverride.workspace_id == workspace_id,
                WorkspaceAssetOverride.match_kind == match_kind,
                WorkspaceAssetOverride.asset_match_key == asset_match_key,
            )
        ).scalar_one_or_none()
