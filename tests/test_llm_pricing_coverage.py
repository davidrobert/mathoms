"""Cobertura: ``MODEL_PRICING`` cobre todo modelo default em produção."""

from __future__ import annotations

import importlib
import logging
from unittest.mock import MagicMock

import pytest

from pipeline.llm import pricing as pricing_mod
from pipeline.llm.litellm_client import LLMService

# Modelos referenciados em código de produção. Atualizar se default mudar.
PRODUCTION_DEFAULT_MODELS: list[str] = [
    "claude-sonnet-4-6",  # config/pipeline.json + backend defaults (ADR-289)
    "claude-haiku-4-5",  # backend/app/services/section_summary_orchestrator.py
]


def _bare_service(model_name: str) -> LLMService:
    svc = LLMService.__new__(LLMService)
    cfg = MagicMock()
    cfg.model_name = model_name
    cfg.provider = "anthropic"
    cfg.api_key = "test"
    svc._config = cfg
    return svc


@pytest.mark.parametrize("model_name", PRODUCTION_DEFAULT_MODELS)
def test_production_default_models_have_pricing(model_name: str) -> None:
    """Default de produção deve estar em ``MODEL_PRICING``; senão FinOps fica cego."""
    svc = _bare_service(model_name)
    cost = svc._estimate_cost(tokens_in=1000, tokens_out=500)
    assert (
        cost is not None
    ), f"Modelo '{model_name}' sem pricing — adicione a pipeline/llm/pricing.py:MODEL_PRICING"
    assert cost > 0


def test_unknown_model_returns_none() -> None:
    svc = _bare_service("modelo-completamente-inventado-xyz-2099")
    assert svc._estimate_cost(1000, 500) is None


def test_unknown_model_emits_warning_once(caplog: pytest.LogCaptureFixture) -> None:
    importlib.reload(pricing_mod)
    svc = _bare_service("zzz-unique-test-model-9999")

    with caplog.at_level(logging.WARNING, logger="mathoms.llm.unknown_model_pricing"):
        svc._estimate_cost(100, 50)
        svc._estimate_cost(200, 100)
        svc._estimate_cost(300, 150)

    relevant = [r for r in caplog.records if r.name == "mathoms.llm.unknown_model_pricing"]
    assert len(relevant) == 1, f"warning emitido {len(relevant)}× (esperado 1)"
    assert "zzz-unique-test-model-9999" in relevant[0].getMessage()


def test_known_model_does_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    importlib.reload(pricing_mod)
    svc = _bare_service("claude-sonnet-4-20250514")

    with caplog.at_level(logging.WARNING, logger="mathoms.llm.unknown_model_pricing"):
        svc._estimate_cost(1000, 500)

    relevant = [r for r in caplog.records if r.name == "mathoms.llm.unknown_model_pricing"]
    assert relevant == []


def test_pricing_table_uses_per_million_tokens_units() -> None:
    """Pega regressão de unidade (per-1k vs per-1M)."""
    for model, rates in pricing_mod.MODEL_PRICING.items():
        assert "input" in rates and "output" in rates, f"{model} faltando keys"
        assert rates["input"] >= 0 and rates["output"] >= 0, f"{model} negativo"
        assert (
            rates["output"] >= rates["input"] * 0.5
        ), f"{model}: output {rates['output']} suspeito vs input {rates['input']}"
