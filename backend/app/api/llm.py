"""LLM Config API — CRUD for per-workspace LLM configuration + connectivity test."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.llm_config import LLMConfig
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.llm import (
    LLMConfigCreateRequest,
    LLMConfigResponse,
    LLMConfigTestRequest,
    LLMConfigTestResponse,
    LLMTierResponse,
)
from backend.app.services.vault import VaultService

router = APIRouter(prefix="/config", tags=["llm"])

_vault = VaultService()


async def _get_workspace(user: User, db: AsyncSession) -> Workspace:
    result = await db.execute(select(Workspace).where(Workspace.owner_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    return ws


def _mask_api_key(key: str) -> str:
    """Show first 4 and last 4 characters, mask the rest."""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def _config_to_response(cfg: LLMConfig) -> LLMConfigResponse:
    api_key_plain = _vault.decrypt(cfg.api_key_encrypted)
    masked = _mask_api_key(api_key_plain) if api_key_plain else "****"
    return LLMConfigResponse(
        id=cfg.id,
        provider=cfg.provider,
        api_key_masked=masked,
        model_name=cfg.model_name,
        max_tokens=cfg.max_tokens,
        temperature=cfg.temperature,
        created_at=cfg.created_at.isoformat() if cfg.created_at else "",
        updated_at=cfg.updated_at.isoformat() if cfg.updated_at else "",
    )


@router.get("/llm", response_model=Optional[LLMConfigResponse])
async def get_llm_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current LLM configuration (API key masked)."""
    ws = await _get_workspace(user, db)
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        return None
    return _config_to_response(cfg)


@router.put("/llm", response_model=LLMConfigResponse, status_code=status.HTTP_200_OK)
async def save_llm_config(
    body: LLMConfigCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update LLM configuration. API key is encrypted at rest via Fernet."""
    ws = await _get_workspace(user, db)
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()

    encrypted_key = _vault.encrypt(body.api_key)

    if cfg:
        cfg.provider = body.provider
        cfg.api_key_encrypted = encrypted_key
        cfg.model_name = body.model_name
        cfg.max_tokens = body.max_tokens
        cfg.temperature = body.temperature
    else:
        cfg = LLMConfig(
            workspace_id=ws.id,
            provider=body.provider,
            api_key_encrypted=encrypted_key,
            model_name=body.model_name,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
        )
        db.add(cfg)

    await db.commit()
    await db.refresh(cfg)
    return _config_to_response(cfg)


@router.delete("/llm", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete LLM configuration (reverts workspace to free tier)."""
    ws = await _get_workspace(user, db)
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuração LLM não encontrada")
    await db.delete(cfg)
    await db.commit()


@router.post("/llm/test", response_model=LLMConfigTestResponse)
async def test_llm_connection(
    body: Optional[LLMConfigTestRequest] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test connectivity with the LLM provider. Uses saved config or override params."""
    from pipeline.llm.service import LLMService, LLMConfig as LLMServiceConfig

    ws = await _get_workspace(user, db)

    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()

    if body and body.api_key:
        provider = body.provider or (cfg.provider if cfg else "anthropic")
        api_key = body.api_key
        model_name = body.model_name or (cfg.model_name if cfg else "claude-sonnet-4-20250514")
    elif cfg:
        provider = body.provider if body and body.provider else cfg.provider
        api_key_plain = _vault.decrypt(cfg.api_key_encrypted)
        if not api_key_plain:
            raise HTTPException(status_code=400, detail="Não foi possível descriptografar a API key")
        api_key = api_key_plain
        model_name = body.model_name if body and body.model_name else cfg.model_name
    else:
        raise HTTPException(status_code=404, detail="Nenhuma configuração LLM encontrada. Salve uma configuração primeiro ou forneça api_key no request.")

    svc_config = LLMServiceConfig(
        provider=provider,
        api_key=api_key,
        model_name=model_name,
    )
    svc = LLMService(svc_config)
    test_result = svc.test_connection()

    return LLMConfigTestResponse(**test_result)


@router.get("/llm/tier", response_model=LLMTierResponse)
async def get_tier(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check current workspace tier (free or premium based on valid LLM config)."""
    ws = await _get_workspace(user, db)
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == ws.id))
    cfg = result.scalar_one_or_none()

    if cfg and cfg.api_key_encrypted:
        return LLMTierResponse(
            tier="premium",
            has_llm_config=True,
            provider=cfg.provider,
            model=cfg.model_name,
        )
    return LLMTierResponse(tier="free", has_llm_config=False)
