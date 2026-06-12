"""Use case: lista modelos disponíveis por provider — catálogo curado (ADR-289 F1)."""

from __future__ import annotations

from backend.app.application.base.errors import ValidationError
from backend.app.schemas.llm import VALID_PROVIDERS, LLMModelInfo, LLMModelsResponse
from pipeline.llm.models_catalog import MODELS_BY_PROVIDER, default_model_for
from pipeline.llm.pricing import estimate_cost_usd


def _to_model_info(value: str, label: str) -> LLMModelInfo:
    # estimate_cost_usd é a semântica real de pricing (substring match em
    # MODEL_PRICING) — não reimplementar com lookup exato.
    pricing_known = estimate_cost_usd(value, 1, 1) is not None
    return LLMModelInfo(value=value, label=label, source="curated", pricing_known=pricing_known)


def get_llm_models(provider: str) -> LLMModelsResponse:
    if provider not in VALID_PROVIDERS:
        raise ValidationError(
            f"Provider inválido: {provider!r}. Esperado um de: {', '.join(VALID_PROVIDERS)}"
        )
    return LLMModelsResponse(
        provider=provider,
        models=[_to_model_info(m.value, m.label) for m in MODELS_BY_PROVIDER.get(provider, ())],
        default_model=default_model_for(provider),
        fetched_dynamic=False,
    )
