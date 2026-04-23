"""Helpers privados do agregado LLMConfig (masking + DTO assembly)."""

from __future__ import annotations

from backend.app.models.llm_config import LLMConfig
from backend.app.schemas.llm import LLMConfigResponse
from backend.app.services.vault import VaultService


def mask_api_key(key: str) -> str:
    """Mostra 4 primeiros + 4 últimos chars, mascara o meio."""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def to_response(cfg: LLMConfig, *, vault: VaultService) -> LLMConfigResponse:
    api_key_plain = vault.decrypt(cfg.api_key_encrypted)
    masked = mask_api_key(api_key_plain) if api_key_plain else "****"
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
