"""Use case: cria ou atualiza config LLM do workspace (upsert)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ValidationError
from backend.app.application.llm_config._response import to_response
from backend.app.models.llm_config import LLMConfig
from backend.app.schemas.llm import LLMConfigCreateRequest, LLMConfigResponse
from backend.app.services.vault import VaultService


def _resolve_encrypted_key(
    body: LLMConfigCreateRequest, cfg: LLMConfig | None, vault: VaultService
) -> str:
    new_key = (body.api_key or "").strip()
    if new_key:
        return vault.encrypt(new_key)
    if cfg is None:
        raise ValidationError("api_key é obrigatória ao criar configuração LLM")
    if body.provider != cfg.provider:
        raise ValidationError("Trocar de provider exige informar a api_key do novo provider")
    return cfg.api_key_encrypted


async def save_llm_config(
    workspace_id: str,
    body: LLMConfigCreateRequest,
    *,
    db: AsyncSession,
    vault: VaultService,
) -> LLMConfigResponse:
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == workspace_id))
    cfg = result.scalar_one_or_none()
    encrypted_key = _resolve_encrypted_key(body, cfg, vault)

    if cfg:
        cfg.provider = body.provider
        cfg.api_key_encrypted = encrypted_key
        cfg.model_name = body.model_name
        if "max_tokens" in body.model_fields_set:
            cfg.max_tokens = body.max_tokens
        if "temperature" in body.model_fields_set:
            cfg.temperature = body.temperature
    else:
        cfg = LLMConfig(
            workspace_id=workspace_id,
            provider=body.provider,
            api_key_encrypted=encrypted_key,
            model_name=body.model_name,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
        )
        db.add(cfg)

    await db.commit()
    await db.refresh(cfg)
    return to_response(cfg, vault=vault)
