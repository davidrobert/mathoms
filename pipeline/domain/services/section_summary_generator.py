"""SectionSummaryGenerator — LLM-driven section summaries (v2.9 · ADR-144)."""
# Boundary (CLAUDE.md §pipeline-não-importa-framework): generator não
# importa fastapi/celery/sqlalchemy/redis. Cache adapter, LLM client e
# fallback são injetados (Protocols + Callable). Telemetry: logger
# ``mathoms.llm.section_summaries`` (ADR-110), sem PII (snapshot_hash
# truncado a 12 chars; nunca loga texto gerado nem snapshot_data).

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Literal, Mapping, Optional, Protocol

from pipeline.llm.schemas.section_summaries import SectionSummaryOutput

logger = logging.getLogger("mathoms.llm.section_summaries")


SectionSummarySource = Literal["llm", "cache", "fallback"]


@dataclass(frozen=True)
class SectionSummaryResult:
    """Resultado de uma chamada do generator."""

    text: str
    source: SectionSummarySource
    latency_ms: int
    fallback_reason: Optional[str] = None
    cost_usd: Decimal = Decimal("0")
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class SectionSummaryGeneratorConfig:
    """Value object de config (ADR-097 D2 — não recebe StageConfig nem Path)."""

    model: str = "claude-haiku-4-5"
    max_tokens: int = 600
    temperature: float = 0.0
    request_timeout_s: float = 8.0
    cache_ttl_s: int = 24 * 60 * 60  # 24h — ADR-144 §2
    # Entra na cache key: bump de prompt-version invalida o cache na hora
    # (sem isso, texto da versão anterior era servido até o TTL expirar).
    prompt_version: str = "0"

    # Custo unitário em USD/1M tokens (Haiku 4.5 default — ADR-144 §5).
    cost_per_million_input_usd: Decimal = Decimal("1.00")
    cost_per_million_output_usd: Decimal = Decimal("5.00")


@dataclass(frozen=True)
class LLMRawResponse:
    """Resposta crua do LLM client (independente do provider)."""

    output: SectionSummaryOutput
    prompt_tokens: int
    completion_tokens: int


class SectionSummaryLLMClient(Protocol):
    """Boundary tipado para o LLM — generator não conhece LiteLLM/Instructor."""

    def call(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        section_id: str,
    ) -> "LLMRawResponse": ...


class SectionSummaryCache(Protocol):
    """Boundary tipado para cache — paridade com ``backend.app.services.llm_cache``."""

    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str, ttl_s: int = ...) -> None: ...


# Callable: ``(section_id, snapshot_data) -> str | None``. Chamado quando
# LLM falha ou está desabilitado.
DeterministicFallback = Callable[[str, Mapping[str, Any]], Optional[str]]


@dataclass(frozen=True)
class PromptTemplate:
    """Template carregado do YAML — system + user (com placeholders)."""

    system_prompt: str
    user_prompt_template: str


@dataclass(frozen=True)
class _GenerateCtx:
    """Bundle de args de ``generate()`` (mantém assinatura curta + tipada)."""

    section_id: str
    snapshot_hash: str
    workspace_id: int
    snapshot_data: Mapping[str, Any]
    start: float


@dataclass(frozen=True)
class _TelemetryEvent:
    """Snapshot de telemetria de uma chamada (sem PII)."""

    section_id: str
    snapshot_hash: str
    latency_ms: int
    cache_hit: bool
    fallback_used: bool
    cost_usd: Decimal = Decimal("0")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error_class: Optional[str] = None


class SectionSummaryGenerator:
    """Gera section summaries com LLM + cache + fallback determinístico."""

    # ADR-111 stateless: sem `lru_cache`/dict global. Config frozen.

    def __init__(
        self,
        *,
        llm_client: SectionSummaryLLMClient,
        cache: SectionSummaryCache,
        fallback: DeterministicFallback,
        templates: Mapping[str, PromptTemplate],
        config: SectionSummaryGeneratorConfig | None = None,
    ) -> None:
        self._llm = llm_client
        self._cache = cache
        self._fallback = fallback
        self._templates = templates
        self._config = config or SectionSummaryGeneratorConfig()

    def generate(
        self,
        *,
        section_id: str,
        snapshot_hash: str,
        workspace_id: int,
        snapshot_data: Mapping[str, Any],
    ) -> SectionSummaryResult:
        """Pipeline: cache → LLM → fallback. Sempre retorna resultado válido."""
        ctx = _GenerateCtx(
            section_id=section_id,
            snapshot_hash=snapshot_hash,
            workspace_id=workspace_id,
            snapshot_data=snapshot_data,
            start=time.monotonic(),
        )
        return self._dispatch(ctx)

    def _dispatch(self, ctx: "_GenerateCtx") -> SectionSummaryResult:
        cache_key = self._cache_key(ctx.workspace_id, ctx.snapshot_hash, ctx.section_id)
        cached = self._check_cache(cache_key)
        if cached is not None:
            return self._result_from_cache(cached, ctx.section_id, ctx.snapshot_hash, ctx.start)
        template = self._templates.get(ctx.section_id)
        if template is None:
            return self._run_fallback(
                ctx.section_id, ctx.snapshot_hash, ctx.snapshot_data, ctx.start, "template_missing"
            )
        return self._call_llm_or_fallback(
            ctx.section_id,
            ctx.snapshot_hash,
            ctx.snapshot_data,
            template,
            cache_key,
            ctx.start,
        )

    def _cache_key(self, workspace_id: int, snapshot_hash: str, section_id: str) -> str:
        version = self._config.prompt_version
        return f"mathoms:llm:section_summary:v{version}:{workspace_id}:{snapshot_hash}:{section_id}"

    def _check_cache(self, cache_key: str) -> Optional[str]:
        try:
            return self._cache.get(cache_key)
        except Exception as exc:  # noqa: BLE001 — falha aberta
            logger.warning("cache_get_failed: %s", exc)
            return None

    def _result_from_cache(
        self,
        text: str,
        section_id: str,
        snapshot_hash: str,
        start: float,
    ) -> SectionSummaryResult:
        latency_ms = int((time.monotonic() - start) * 1000)
        self._emit_telemetry(_TelemetryEvent(section_id, snapshot_hash, latency_ms, True, False))
        return SectionSummaryResult(text=text, source="cache", latency_ms=latency_ms)

    def _call_llm_or_fallback(
        self,
        section_id: str,
        snapshot_hash: str,
        snapshot_data: Mapping[str, Any],
        template: PromptTemplate,
        cache_key: str,
        start: float,
    ) -> SectionSummaryResult:
        try:
            raw = self._invoke_llm(template, snapshot_data, section_id)
        except Exception as exc:  # noqa: BLE001 — boundary aberto
            return self._run_fallback(
                section_id, snapshot_hash, snapshot_data, start, _classify_llm_error(exc)
            )
        return self._build_llm_result(raw, section_id, snapshot_hash, cache_key, start)

    def _invoke_llm(
        self,
        template: PromptTemplate,
        snapshot_data: Mapping[str, Any],
        section_id: str,
    ) -> LLMRawResponse:
        user_prompt = self._render_user_prompt(template, snapshot_data)
        return self._llm.call(
            system_prompt=template.system_prompt,
            user_prompt=user_prompt,
            section_id=section_id,
        )

    def _build_llm_result(
        self,
        raw: LLMRawResponse,
        section_id: str,
        snapshot_hash: str,
        cache_key: str,
        start: float,
    ) -> SectionSummaryResult:
        text = raw.output.summary_md
        cost = self._estimate_cost(raw.prompt_tokens, raw.completion_tokens)
        self._write_cache(cache_key, text)
        latency_ms = int((time.monotonic() - start) * 1000)
        self._emit_telemetry(_llm_success_event(raw, section_id, snapshot_hash, latency_ms, cost))
        return _result_from_raw(raw, text, cost, latency_ms)

    def _render_user_prompt(
        self,
        template: PromptTemplate,
        snapshot_data: Mapping[str, Any],
    ) -> str:
        payload = json.dumps(snapshot_data, ensure_ascii=False, default=str)
        return template.user_prompt_template.replace("{section_data_json}", payload)

    def _write_cache(self, cache_key: str, text: str) -> None:
        try:
            self._cache.set(cache_key, text, self._config.cache_ttl_s)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache_set_failed: %s", exc)

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> Decimal:
        cfg = self._config
        million = Decimal("1000000")
        in_cost = (Decimal(prompt_tokens) / million) * cfg.cost_per_million_input_usd
        out_cost = (Decimal(completion_tokens) / million) * cfg.cost_per_million_output_usd
        return (in_cost + out_cost).quantize(Decimal("0.000001"))

    def _run_fallback(
        self,
        section_id: str,
        snapshot_hash: str,
        snapshot_data: Mapping[str, Any],
        start: float,
        reason: str,
    ) -> SectionSummaryResult:
        text = self._fallback(section_id, snapshot_data) or ""
        latency_ms = int((time.monotonic() - start) * 1000)
        self._emit_telemetry(_fallback_event(section_id, snapshot_hash, latency_ms, reason))
        return SectionSummaryResult(
            text=text,
            source="fallback",
            latency_ms=latency_ms,
            fallback_reason=reason,
        )

    def _emit_telemetry(self, event: _TelemetryEvent) -> None:
        # Sem PII: snapshot_hash truncado, sem workspace_id, sem texto gerado.
        logger.info(
            "section_summary_generated",
            extra={
                "section_id": event.section_id,
                "snapshot_hash": event.snapshot_hash[:12],
                "latency_ms": event.latency_ms,
                "cache_hit": event.cache_hit,
                "fallback_used": event.fallback_used,
                "cost_usd": str(event.cost_usd),
                "prompt_tokens": event.prompt_tokens,
                "completion_tokens": event.completion_tokens,
                "model": self._config.model,
                "error_class": event.error_class,
            },
        )


def _result_from_raw(
    raw: LLMRawResponse,
    text: str,
    cost: Decimal,
    latency_ms: int,
) -> SectionSummaryResult:
    return SectionSummaryResult(
        text=text,
        source="llm",
        latency_ms=latency_ms,
        cost_usd=cost,
        prompt_tokens=raw.prompt_tokens,
        completion_tokens=raw.completion_tokens,
    )


def _llm_success_event(
    raw: LLMRawResponse,
    section_id: str,
    snapshot_hash: str,
    latency_ms: int,
    cost: Decimal,
) -> "_TelemetryEvent":
    return _TelemetryEvent(
        section_id=section_id,
        snapshot_hash=snapshot_hash,
        latency_ms=latency_ms,
        cache_hit=False,
        fallback_used=False,
        cost_usd=cost,
        prompt_tokens=raw.prompt_tokens,
        completion_tokens=raw.completion_tokens,
    )


def _fallback_event(
    section_id: str,
    snapshot_hash: str,
    latency_ms: int,
    reason: str,
) -> "_TelemetryEvent":
    return _TelemetryEvent(
        section_id=section_id,
        snapshot_hash=snapshot_hash,
        latency_ms=latency_ms,
        cache_hit=False,
        fallback_used=True,
        error_class=reason,
    )


_RATE_LIMIT_HINTS = ("429", "rate limit", "rate_limit", "too many requests")
_TIMEOUT_HINTS = ("timeout", "timed out")
_INVALID_JSON_HINTS = ("validation", "pydantic", "instructor")


def _classify_llm_error(exc: Exception) -> str:
    """Classifica exceção do LLM em ``error_class`` para telemetria."""
    msg = str(exc).lower()
    if any(h in msg for h in _RATE_LIMIT_HINTS):
        return "rate_limit"
    if any(h in msg for h in _TIMEOUT_HINTS):
        return "timeout"
    if any(h in msg for h in _INVALID_JSON_HINTS):
        return "invalid_json"
    return "provider_5xx"


def load_prompt_templates_from_yaml(yaml_path: str) -> dict[str, PromptTemplate]:
    """Carrega ``config/prompts/section_summaries.yaml`` para o generator."""
    # Adapter síncrono; chamado uma vez na construção do generator.
    import yaml

    with open(yaml_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    system = str(raw.get("system_prompt", "")).strip()
    sections = raw.get("sections", {}) or {}
    return _build_template_map(system, sections)


def load_prompt_version_from_yaml(yaml_path: str) -> str:
    """Lê a ``version:`` do YAML de prompts (entra na cache key)."""
    import yaml

    with open(yaml_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return str(raw.get("version", "0")).strip() or "0"


def _build_template_map(system: str, sections: Mapping[str, Any]) -> dict[str, PromptTemplate]:
    templates: dict[str, PromptTemplate] = {}
    for section_id, entry in sections.items():
        user_template = str((entry or {}).get("user_prompt", "")).strip()
        if not user_template:
            continue
        templates[str(section_id)] = PromptTemplate(
            system_prompt=system,
            user_prompt_template=user_template,
        )
    return templates
