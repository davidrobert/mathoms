"""Goldens para SectionSummaryGenerator (v2.9 · ADR-144)."""
# 6+ cenários: LLM success, cache hit, timeout, rate limit (HTTP 429),
# invalid JSON (validation), cache write→read entre chamadas. Sem bater
# Anthropic em CI (FakeLLMClient nomeado em tests/fakes/llm.py).

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.section_summary_generator import (
    PromptTemplate,
    SectionSummaryGenerator,
    SectionSummaryGeneratorConfig,
)

from backend.app.services.llm_cache import InMemoryLLMCache
from tests.fakes.llm import FakeLLMRaisingClient, FakeLLMSuccess, make_fake_fallback


_TEMPLATE = PromptTemplate(
    system_prompt="You are a financial editor.",
    user_prompt_template="Section S1 data: {section_data_json}",
)
_TEMPLATES = {"S1": _TEMPLATE}


def _make_generator(*, llm, fallback_text="fallback determinístico", config=None):
    return SectionSummaryGenerator(
        llm_client=llm,
        cache=InMemoryLLMCache(),
        fallback=make_fake_fallback(fallback_text),
        templates=_TEMPLATES,
        config=config or SectionSummaryGeneratorConfig(),
    )


def _make_generator_with_cache(*, llm, cache, fallback_text="fallback"):
    return SectionSummaryGenerator(
        llm_client=llm,
        cache=cache,
        fallback=make_fake_fallback(fallback_text),
        templates=_TEMPLATES,
        config=SectionSummaryGeneratorConfig(),
    )


# ─── Cenário 1: LLM success ─────────────────────────────────────────


def test_llm_success_returns_source_llm():
    fake = FakeLLMSuccess(text="LLM gerou este texto.", prompt_tokens=2000, completion_tokens=500)
    gen = _make_generator(llm=fake)
    result = gen.generate(
        section_id="S1",
        snapshot_hash="hash" + "0" * 60,
        workspace_id=1,
        snapshot_data={"patrimonio": {"liquido": 100}},
    )
    assert result.source == "llm"
    assert result.text == "LLM gerou este texto."
    assert result.prompt_tokens == 2000
    assert result.completion_tokens == 500
    assert result.cost_usd > Decimal("0")
    assert result.fallback_reason is None
    assert fake.calls == 1


# ─── Cenário 2: Cache hit ───────────────────────────────────────────


def test_cache_hit_skips_llm_call():
    cache = InMemoryLLMCache()
    cache_key = "mathoms:llm:section_summary:1:precachehash:S1"
    cache.set(cache_key, "Texto cacheado prévio.", ttl_s=3600)
    fake = FakeLLMSuccess(text="Não deveria ser chamado.")
    gen = _make_generator_with_cache(llm=fake, cache=cache)
    result = gen.generate(
        section_id="S1",
        snapshot_hash="precachehash",
        workspace_id=1,
        snapshot_data={"x": 1},
    )
    assert result.source == "cache"
    assert result.text == "Texto cacheado prévio."
    assert fake.calls == 0  # LLM não chamado em hit


# ─── Cenário 3: LLM timeout → fallback ──────────────────────────────


def test_llm_timeout_falls_back_with_reason_timeout():
    fake = FakeLLMRaisingClient(error=TimeoutError("request timed out after 8s"))
    gen = _make_generator(llm=fake, fallback_text="determinístico-timeout")
    result = gen.generate(
        section_id="S1",
        snapshot_hash="hash_timeout",
        workspace_id=1,
        snapshot_data={"x": 1},
    )
    assert result.source == "fallback"
    assert result.text == "determinístico-timeout"
    assert result.fallback_reason == "timeout"


# ─── Cenário 4: LLM rate limit (HTTP 429) → fallback ────────────────


def test_llm_rate_limit_falls_back_with_reason_rate_limit():
    fake = FakeLLMRaisingClient(error=RuntimeError("HTTP 429: too many requests"))
    gen = _make_generator(llm=fake, fallback_text="determinístico-rl")
    result = gen.generate(
        section_id="S1",
        snapshot_hash="hash_rl",
        workspace_id=1,
        snapshot_data={"x": 1},
    )
    assert result.source == "fallback"
    assert result.fallback_reason == "rate_limit"
    assert result.text == "determinístico-rl"


# ─── Cenário 5: LLM JSON inválido (Instructor parse error) ──────────


def test_llm_invalid_json_falls_back_with_reason_invalid_json():
    fake = FakeLLMRaisingClient(error=ValueError("pydantic validation error: missing summary_md"))
    gen = _make_generator(llm=fake, fallback_text="determinístico-json")
    result = gen.generate(
        section_id="S1",
        snapshot_hash="hash_json",
        workspace_id=1,
        snapshot_data={"x": 1},
    )
    assert result.source == "fallback"
    assert result.fallback_reason == "invalid_json"


# ─── Cenário 6: Cache write após LLM success → próxima chamada hit ─


def test_cache_populated_after_llm_call():
    cache = InMemoryLLMCache()
    fake = FakeLLMSuccess(text="primeira chamada texto.")
    gen = _make_generator_with_cache(llm=fake, cache=cache)
    snapshot_data = {"patrimonio": {"liquido": 100}}
    kwargs = {"section_id": "S1", "snapshot_hash": "h", "workspace_id": 1}
    first = gen.generate(snapshot_data=snapshot_data, **kwargs)
    second = gen.generate(snapshot_data=snapshot_data, **kwargs)
    assert first.source == "llm"
    assert second.source == "cache"
    assert second.text == first.text
    assert fake.calls == 1


# ─── Cenário extra: Template missing → fallback com reason ──────────


def test_unknown_section_id_falls_back_with_reason_template_missing():
    fake = FakeLLMSuccess()
    gen = _make_generator(llm=fake, fallback_text="determinístico-unknown")
    result = gen.generate(
        section_id="UNKNOWN_SECTION",
        snapshot_hash="hash_unknown",
        workspace_id=1,
        snapshot_data={"x": 1},
    )
    assert result.source == "fallback"
    assert result.fallback_reason == "template_missing"
    assert fake.calls == 0


# ─── Cenário extra: cost_usd Decimal (ADR-090) ──────────────────────


def test_cost_usd_is_decimal_haiku_pricing():
    fake = FakeLLMSuccess(prompt_tokens=2000, completion_tokens=500)
    gen = _make_generator(llm=fake)
    result = gen.generate(
        section_id="S1",
        snapshot_hash="hash_cost",
        workspace_id=1,
        snapshot_data={"x": 1},
    )
    # Haiku 4.5: 1.00/M input + 5.00/M output
    # 2000/1e6 * 1.00 + 500/1e6 * 5.00 = 0.002 + 0.0025 = 0.0045
    assert isinstance(result.cost_usd, Decimal)
    assert result.cost_usd == Decimal("0.004500")


# ─── Cenário extra: cache key formato canônico ──────────────────────


def test_cache_key_format_matches_adr_144():
    fake = FakeLLMSuccess()
    cache = InMemoryLLMCache()
    gen = _make_generator_with_cache(llm=fake, cache=cache)
    gen.generate(
        section_id="S1",
        snapshot_hash="abc123",
        workspace_id=42,
        snapshot_data={"x": 1},
    )
    expected_key = "mathoms:llm:section_summary:42:abc123:S1"
    assert cache.get(expected_key) is not None


# ─── Cenário extra: SectionSummaryOutput valida tone ────────────────


def test_section_summary_output_rejects_invalid_tone():
    from pipeline.llm.schemas.section_summaries import SectionSummaryOutput

    with pytest.raises(Exception):
        SectionSummaryOutput(summary_md="ok " * 5, tone="invalid_tone")  # type: ignore[arg-type]
