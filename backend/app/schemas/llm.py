"""Pydantic schemas for LLM configuration endpoints."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

VALID_PROVIDERS = ("anthropic", "openai", "ollama", "groq", "deepseek", "together_ai")


class LLMConfigCreateRequest(BaseModel):
    """Create or update LLM configuration for a workspace."""

    provider: str = Field(
        ..., description="LLM provider (anthropic, openai, ollama, groq, deepseek, together_ai)"
    )
    api_key: str = Field(..., min_length=1, description="API key (will be encrypted at rest)")
    model_name: str = Field(default="claude-sonnet-4-20250514", min_length=1, max_length=100)
    max_tokens: int = Field(default=4096, ge=1, le=200000)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in VALID_PROVIDERS:
            raise ValueError(f"Provider must be one of: {', '.join(VALID_PROVIDERS)}")
        return v


class LLMConfigResponse(BaseModel):
    """LLM config response — API key is masked."""

    id: str
    provider: str
    api_key_masked: str = Field(..., description="Masked API key (first 4 + last 4 chars)")
    api_key_status: Literal["valid", "invalid"] = Field(
        default="valid",
        description=(
            "'invalid' quando o ciphertext não decripta com a FERNET_KEY atual "
            "(rotação) ou decripta para vazio. Sinal para a UI pedir re-save."
        ),
    )
    model_name: str
    max_tokens: int
    temperature: float
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class LLMConfigTestRequest(BaseModel):
    """Test LLM connectivity with current config or override params."""

    provider: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None


class LLMConfigTestResponse(BaseModel):
    success: bool
    provider: str
    model: str
    response: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    duration_ms: int = 0


class LLMTierResponse(BaseModel):
    """Current tier based on LLM config validity."""

    tier: str = Field(..., description="'free' or 'premium'")
    has_llm_config: bool
    provider: Optional[str] = None
    model: Optional[str] = None
