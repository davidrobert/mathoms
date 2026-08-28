"""Persistência das declarações de lastro do usuário ([[ADR-224]] §5).

Extraído de `exposicao_cambial_v2` na [[A40.l80]]: aquele módulo computa o CARD e este
guarda o que a família declarou — eixos ortogonais que dividiam um arquivo cronicamente no
teto de 500 linhas, o que já bloqueou três PRs seguidos. A extração é movimento puro:
nenhuma assinatura muda, nenhum comportamento muda.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.asset_catalog import WorkspaceAssetOverride
from backend.app.schemas.dto.exposicao_cambial import (
    AssetOverrideCommand,
    AssetOverrideResponse,
)


def _to_override_response(row: WorkspaceAssetOverride) -> AssetOverrideResponse:
    return AssetOverrideResponse(
        id=row.id,
        workspace_id=row.workspace_id,
        match_kind=row.match_kind,
        asset_match_key=row.asset_match_key,
        lastro_moeda=row.lastro_moeda,
        override_source=row.override_source,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by_user_id=row.created_by_user_id,
    )


async def _find_override(
    db: AsyncSession, workspace_id: str, match_kind: str, asset_match_key: str
) -> Optional[WorkspaceAssetOverride]:
    stmt = select(WorkspaceAssetOverride).where(
        WorkspaceAssetOverride.workspace_id == workspace_id,
        WorkspaceAssetOverride.match_kind == match_kind,
        WorkspaceAssetOverride.asset_match_key == asset_match_key,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _new_override_row(
    workspace_id: str, command: AssetOverrideCommand, user_id: Optional[str] = None
) -> WorkspaceAssetOverride:
    now = datetime.now(timezone.utc)
    return WorkspaceAssetOverride(
        workspace_id=workspace_id,
        match_kind=command.match_kind,
        asset_match_key=command.asset_match_key,
        lastro_moeda=command.lastro_moeda,
        override_source="user_manual",
        created_by_user_id=user_id,
        created_at=now,
        updated_at=now,
    )


async def _create_override(
    db: AsyncSession,
    workspace_id: str,
    command: AssetOverrideCommand,
    user_id: Optional[str] = None,
) -> WorkspaceAssetOverride:
    row = _new_override_row(workspace_id, command, user_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def _update_override(
    db: AsyncSession,
    existing: WorkspaceAssetOverride,
    lastro_moeda: str,
    user_id: Optional[str] = None,
) -> WorkspaceAssetOverride:
    existing.lastro_moeda = lastro_moeda
    existing.updated_at = datetime.now(timezone.utc)
    if user_id is not None:
        existing.created_by_user_id = user_id
    await db.commit()
    await db.refresh(existing)
    return existing


async def upsert_asset_override(
    workspace_id: str,
    command: AssetOverrideCommand,
    db: AsyncSession,
    user_id: Optional[str] = None,
) -> AssetOverrideResponse:
    """Upsert sticky pattern ADR-215 — mesma `(ws, kind, key)` atualiza in-place."""
    existing = await _find_override(db, workspace_id, command.match_kind, command.asset_match_key)
    if existing is None:
        row = await _create_override(db, workspace_id, command, user_id)
    else:
        row = await _update_override(db, existing, command.lastro_moeda, user_id)
    return _to_override_response(row)


async def delete_asset_override(
    workspace_id: str, match_kind: str, asset_match_key: str, db: AsyncSession
) -> bool:
    """Remove override per-workspace. Retorna True se removeu, False se não existia."""
    existing = await _find_override(db, workspace_id, match_kind, asset_match_key)
    if existing is None:
        return False
    await db.delete(existing)
    await db.commit()
    return True


async def list_asset_overrides(workspace_id: str, db: AsyncSession) -> list[AssetOverrideResponse]:
    stmt = select(WorkspaceAssetOverride).where(WorkspaceAssetOverride.workspace_id == workspace_id)
    result = await db.execute(stmt)
    return [_to_override_response(r) for r in result.scalars().all()]
