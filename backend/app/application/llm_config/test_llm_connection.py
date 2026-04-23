"""Use case: testa conectividade com provider LLM (override ou config salva)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.models.llm_config import LLMConfig
from backend.app.schemas.llm import LLMConfigTestRequest, LLMConfigTestResponse
from backend.app.services.vault import VaultService


async def test_llm_connection(
    workspace_id: str,
    body: LLMConfigTestRequest | None,
    *,
    db: AsyncSession,
    vault: VaultService,
) -> LLMConfigTestResponse:
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == workspace_id))
    cfg = result.scalar_one_or_none()
    provider, api_key, model_name = _resolve_credentials(cfg, body, vault=vault)
    return _probe(provider, api_key, model_name)


def _resolve_credentials(
    cfg: LLMConfig | None,
    body: LLMConfigTestRequest | None,
    *,
    vault: VaultService,
) -> tuple[str, str, str]:
    if body and body.api_key:
        provider = body.provider or (cfg.provider if cfg else "anthropic")
        model_name = body.model_name or (cfg.model_name if cfg else "claude-sonnet-4-20250514")
        return provider, body.api_key, model_name
    if cfg is None:
        raise NotFoundError(
            "Nenhuma configuração LLM encontrada. Salve uma configuração primeiro "
            "ou forneça api_key no request.",
        )
    provider = body.provider if body and body.provider else cfg.provider
    api_key_plain = vault.decrypt(cfg.api_key_encrypted)
    if not api_key_plain:
        raise ValidationError("Não foi possível descriptografar a API key")
    model_name = body.model_name if body and body.model_name else cfg.model_name
    return provider, api_key_plain, model_name


def _probe(provider: str, api_key: str, model_name: str) -> LLMConfigTestResponse:
    from pipeline.llm.litellm_client import LLMConfig as LLMServiceConfig
    from pipeline.llm.litellm_client import LLMService

    svc = LLMService(LLMServiceConfig(provider=provider, api_key=api_key, model_name=model_name))
    return LLMConfigTestResponse(**svc.test_connection())
