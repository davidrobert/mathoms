"""Invariantes do catálogo de modelos LLM (ADR-288)."""

from __future__ import annotations

import pytest

from pipeline.llm.models_catalog import (
    DEPRECATED_MODELS,
    MODELS_BY_PROVIDER,
    PARECER_MODEL,
    SUPPORTED_PROVIDERS,
    default_model_for,
)
from pipeline.llm.pricing import estimate_cost_usd

#: Providers cujo pricing é rastreado em MODEL_PRICING — modelo curado desses
#: providers SEM pricing é regressão de tracking de custo (ADR-288 §1).
_PRICED_PROVIDERS = ("anthropic", "openai", "google", "deepseek", "openrouter")


@pytest.mark.parametrize("provider", sorted(MODELS_BY_PROVIDER))
def test_provider_curado_é_suportado(provider: str):
    assert provider in SUPPORTED_PROVIDERS, f"{provider} sem entry em SUPPORTED_PROVIDERS"


@pytest.mark.parametrize("provider", sorted(MODELS_BY_PROVIDER))
def test_default_está_no_catálogo_e_não_é_deprecated(provider: str):
    default = default_model_for(provider)
    values = {m.value for m in MODELS_BY_PROVIDER[provider]}
    assert default in values, f"default {default!r} fora do catálogo de {provider}"
    assert default not in DEPRECATED_MODELS


@pytest.mark.parametrize("provider", _PRICED_PROVIDERS)
def test_modelo_curado_de_provider_precificado_tem_pricing(provider: str):
    # estimate_cost_usd é a semântica real (substring match em MODEL_PRICING).
    sem_pricing = [
        m.value for m in MODELS_BY_PROVIDER[provider] if estimate_cost_usd(m.value, 1, 1) is None
    ]
    assert not sem_pricing, f"modelos de {provider} sem pricing: {sem_pricing}"


def test_modelo_deprecated_fora_do_catálogo():
    curados = {m.value for models in MODELS_BY_PROVIDER.values() for m in models}
    assert not curados & DEPRECATED_MODELS


def test_parecer_model_tem_prefixo_litellm_e_pricing():
    provider, _, model = PARECER_MODEL.partition("/")
    assert SUPPORTED_PROVIDERS[provider]["prefix"] == f"{provider}/"
    assert estimate_cost_usd(model, 1, 1) is not None
    assert model not in DEPRECATED_MODELS


def test_google_usa_prefixo_gemini():
    # Erro clássico: "google/" passa local e falha em prod (env GEMINI_API_KEY).
    assert SUPPORTED_PROVIDERS["google"] == {"prefix": "gemini/", "env_key": "GEMINI_API_KEY"}


def test_openrouter_registrado():
    assert SUPPORTED_PROVIDERS["openrouter"]["prefix"] == "openrouter/"
