"""Tabela de preços LLM + ``estimate_cost_usd`` retornando ``None`` em modelo desconhecido."""

from __future__ import annotations

import logging
from typing import Optional

MODEL_PRICING: dict[str, dict[str, float]] = {
    # Anthropic — Claude 4.x family (2026; preços oficiais docs.anthropic.com)
    "claude-opus-4-7": {"input": 5.0, "output": 25.0},
    "claude-opus-4-6": {"input": 5.0, "output": 25.0},
    "claude-opus-4-5": {"input": 5.0, "output": 25.0},
    "claude-opus-4-1": {"input": 15.0, "output": 75.0},
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "claude-haiku-4": {"input": 1.0, "output": 5.0},
    # Anthropic — legados ainda em circulação
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku": {"input": 1.0, "output": 5.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    # OpenAI — GPT-5.x family (2026)
    "gpt-5.5": {"input": 5.0, "output": 30.0},
    "gpt-5.5-pro": {"input": 30.0, "output": 180.0},
    "gpt-5.4": {"input": 2.5, "output": 15.0},
    "gpt-5.4-pro": {"input": 30.0, "output": 180.0},
    "gpt-5.4-mini": {"input": 0.75, "output": 4.5},
    "gpt-5.4-nano": {"input": 0.20, "output": 1.25},
    "gpt-5": {"input": 1.25, "output": 10.0},
    "gpt-5-mini": {"input": 0.25, "output": 2.0},
    "gpt-5-nano": {"input": 0.05, "output": 0.40},
    # OpenAI — o-series (reasoning)
    "o3": {"input": 2.0, "output": 8.0},
    "o3-pro": {"input": 20.0, "output": 80.0},
    "o1-preview": {"input": 15.0, "output": 60.0},
    "o1-mini": {"input": 3.0, "output": 12.0},
    # OpenAI — GPT-4.x (legados)
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4.1": {"input": 2.0, "output": 8.0},
    "gpt-4.1-mini": {"input": 0.4, "output": 1.6},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    # Google Gemini (preços referência 2026; ajustar se mudarem)
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.0},
}


_WARNED_UNKNOWN_MODELS: set[str] = set()


def _resolve_pricing(model_name: str) -> Optional[dict[str, float]]:
    pricing = MODEL_PRICING.get(model_name)
    if pricing:
        return pricing
    for prefix, rates in MODEL_PRICING.items():
        if prefix in model_name:
            return rates
    return None


def estimate_cost_usd(model_name: str, tokens_in: int, tokens_out: int) -> Optional[float]:
    """Custo estimado em USD; ``None`` se modelo desconhecido."""
    pricing = _resolve_pricing(model_name)
    if pricing is None:
        _warn_unknown_model_once(model_name)
        return None
    return (tokens_in * pricing["input"] + tokens_out * pricing["output"]) / 1_000_000


def _warn_unknown_model_once(model_name: str) -> None:
    """WARNING único por modelo desconhecido (cache lazy, evita log spam)."""
    if model_name in _WARNED_UNKNOWN_MODELS:
        return
    _WARNED_UNKNOWN_MODELS.add(model_name)
    logging.getLogger("mathoms.llm.unknown_model_pricing").warning(
        "Modelo LLM '%s' sem pricing em MODEL_PRICING — cost_estimate_usd "
        "será 0.0 mas cost_known=False. Adicione o modelo a "
        "pipeline/llm/pricing.py:MODEL_PRICING para habilitar tracking.",
        model_name,
    )
