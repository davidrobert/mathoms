"""Regressão de signature da cascata apólice Haiku→Sonnet (PR #422 quebra reproduzível com fake signature-strict, [[ADR-239]] D6)."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm.litellm_client import LLMCallResult, LLMConfig, LLMService
from pipeline.stages.extract_comprovantes_bens import (
    _APOLICE_HAIKU_MODEL,
    _APOLICE_SONNET_MODEL,
    _build_stage_llm,
    _extract_apolice,
    _StageLLM,
)

# ─────────────────────── signature contract ───────────────────────────────


_EXPECTED_CALL_KWARGS = frozenset(
    {
        "system_prompt",
        "user_prompt",
        "output_schema",
        "max_retries",
        "max_tokens",
        "temperature",
        "stage",
        "image_bytes",
        "image_media_type",
    }
)


def test_llmservice_call_signature_nao_aceita_model_kwarg():
    """Guardrail: se alguém adicionar ``model`` em LLMService.call, este teste falha
    e força repensar a forma como apolice cascata seleciona modelo (via service
    pré-bound, não via kwarg)."""
    sig = inspect.signature(LLMService.call)
    actual = set(sig.parameters.keys()) - {"self"}
    assert actual == _EXPECTED_CALL_KWARGS, (
        f"LLMService.call signature drift: actual={actual} expected={_EXPECTED_CALL_KWARGS}. "
        f"Se for adição intencional, atualize este teste E revise pipeline/stages/extract_comprovantes_bens.py."
    )


# ─────────────────────── FakeLLMService (signature-strict) ─────────────────


class _FakeApoliceOutput:
    """Mock do output Pydantic — só model_dump."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def model_dump(self, mode: str = "json") -> dict:  # noqa: ARG002
        return dict(self._data)


def _minimal_apolice_dict(*, bens: int = 1, confidence: float = 0.95) -> dict:
    return {
        "apolice_numero": "X1",
        "seguradora": "porto",
        "vigencia_inicio": "2026-03-01",
        "vigencia_fim": "2027-03-01",
        "premio_total_brl": "1000.00",
        "forma_pagamento": "cartao",
        "confidence": confidence,
        "bens_segurados": [{"tipo": "veiculo"}] * bens,
        "prompt_version": "old",
    }


_REAL_CALL_SIG = inspect.signature(LLMService.call)


class FakeLLMService:
    """Honra a signature real de ``LLMService.call`` via ``bind`` — kwarg extra (ex.: ``model``) levanta ``TypeError``."""

    def __init__(self, label: str, payload: dict) -> None:
        self.label = label
        self._payload = payload
        self.calls: list[dict] = []

    def call(self, **kwargs) -> LLMCallResult:
        _REAL_CALL_SIG.bind(self, **kwargs)  # TypeError se kwarg desconhecida ou required ausente
        self.calls.append({k: kwargs.get(k) for k in ("stage", "max_tokens", "output_schema")})
        return LLMCallResult(
            output=_FakeApoliceOutput(self._payload),
            provider="anthropic",
            model=self.label,
            tokens_in=10,
            tokens_out=20,
            cost_estimate_usd=0.001,
        )


def _build_fake_stage_llm(
    haiku_payload: dict, sonnet_payload: dict | None = None
) -> tuple[_StageLLM, FakeLLMService, FakeLLMService]:
    haiku = FakeLLMService("haiku", haiku_payload)
    sonnet = FakeLLMService("sonnet", sonnet_payload or haiku_payload)
    crlv = FakeLLMService("crlv-noop", {})
    return _StageLLM(crlv=crlv, apolice_haiku=haiku, apolice_sonnet=sonnet), haiku, sonnet


class _Cfg:
    max_tokens = 4096


# ─────────────────────── cascade dispatch ────────────────────────────────


def test_extract_apolice_uses_haiku_only_when_simple(tmp_path: Path):
    """Bem único + confidence alto → só Haiku service é chamado."""
    pdf = tmp_path / "apolice_simples.pdf"
    pdf.write_bytes(b"%PDF-1.4 simples")
    llm, haiku, sonnet = _build_fake_stage_llm(_minimal_apolice_dict(bens=1, confidence=0.95))

    payload, _, _ = _extract_apolice(pdf, "apolice de auto Toro Cross", llm, _Cfg())

    assert len(haiku.calls) == 1
    assert len(sonnet.calls) == 0
    assert payload["cascade_triggered"] is False


def test_extract_apolice_cascades_to_sonnet_on_multi_bem(tmp_path: Path):
    """Multi-bem em Haiku → cascade para Sonnet service (gate ADR-239 D6)."""
    pdf = tmp_path / "apolice_combinada.pdf"
    pdf.write_bytes(b"%PDF-1.4 combinada")
    haiku_payload = _minimal_apolice_dict(bens=2, confidence=0.95)
    sonnet_payload = _minimal_apolice_dict(bens=2, confidence=0.95)
    llm, haiku, sonnet = _build_fake_stage_llm(haiku_payload, sonnet_payload)

    payload, _, _ = _extract_apolice(pdf, "apolice combinada residencial+auto", llm, _Cfg())

    assert len(haiku.calls) == 1
    assert len(sonnet.calls) == 1
    assert payload["cascade_triggered"] is True


def test_extract_apolice_cache_key_distingue_haiku_e_sonnet(tmp_path: Path):
    """Cache key apolice inclui ``haiku``/``sonnet`` label ([[ADR-144]] idempotência por modelo)."""
    pdf = tmp_path / "apolice_combinada.pdf"
    pdf.write_bytes(b"%PDF-1.4 combinada")
    llm, haiku, sonnet = _build_fake_stage_llm(_minimal_apolice_dict(bens=2))

    _extract_apolice(pdf, "combinada", llm, _Cfg())

    assert "haiku" in haiku.calls[0]["stage"]
    assert "sonnet" in sonnet.calls[0]["stage"]


# ─────────────────────── _build_stage_llm ────────────────────────────────


def test_build_stage_llm_anthropic_usa_modelos_hardcoded():
    """Anthropic: apolice_haiku e apolice_sonnet ganham IDs canônicos ([[ADR-239]] D6)."""
    base = LLMConfig(provider="anthropic", api_key="sk-x", model_name="claude-sonnet-4-6")

    llm = _build_stage_llm(base)

    assert llm.apolice_haiku._config.model_name == _APOLICE_HAIKU_MODEL
    assert llm.apolice_sonnet._config.model_name == _APOLICE_SONNET_MODEL
    # CRLV continua com modelo workspace
    assert llm.crlv._config.model_name == "claude-sonnet-4-6"


def test_build_stage_llm_non_anthropic_degrada_para_workspace_default():
    """Outros providers: cascade roda mas com mesmo modelo — graceful, sem crash."""
    base = LLMConfig(provider="openai", api_key="sk-x", model_name="gpt-4o-mini")

    llm = _build_stage_llm(base)

    assert llm.apolice_haiku._config.model_name == "gpt-4o-mini"
    assert llm.apolice_sonnet._config.model_name == "gpt-4o-mini"


def test_build_stage_llm_preserva_api_key_e_temperatura():
    """Cascade não vaza credencial entre providers; replace() preserva campos não-model."""
    base = LLMConfig(
        provider="anthropic",
        api_key="sk-test-123",
        model_name="claude-sonnet-4-6",
        temperature=0.3,
        max_tokens=8000,
    )

    llm = _build_stage_llm(base)

    for svc in (llm.apolice_haiku, llm.apolice_sonnet, llm.crlv):
        assert svc._config.api_key == "sk-test-123"
        assert svc._config.temperature == 0.3
        assert svc._config.max_tokens == 8000


# ─────────────────────── proof: old broken call() would fail ──────────────


def test_fake_service_rejects_unknown_model_kwarg():
    """Sanidade: FakeLLMService bate o erro real (sem ``model`` kwarg). Garante que
    este harness teria pego o bug do PR #422 antes de mergear."""
    haiku = FakeLLMService("h", _minimal_apolice_dict())
    with pytest.raises(TypeError, match="model"):
        haiku.call(
            system_prompt="x",
            user_prompt="y",
            output_schema=dict,
            max_tokens=4096,
            stage="t",
            model="sonnet",  # type: ignore[call-arg]
        )
